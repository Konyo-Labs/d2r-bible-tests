# -*- coding: utf-8 -*-
"""#245 — THE 👤 CHARACTERS TAB IS THE MANUAL SIDE, AND IT IS SEPARATE FROM THE VAULT.

His words (2026-09-26): "mules and the character build should be somewhat separated.. the structure could be left
like this no problem i like it, but remember all the items getting vaulted and vaulted by AI READERS or manually
should be to the dedicated mules alone.... we should have a separate section for MAIN characters for the builds and
character pinpointing and items" · "i want a separate section for the character MAIN character and builds and easily
deleted and saved as the main character just like the mules have their designated areas" · asked where: "Its own top
tab" · "we dont want those items ending up in character builds accidentally" · "regardless of what i manually do in
the character builds section ... the vault and its logic... should still be doing it job ... so these are separted".

This law drives the SHIPPED pieces, each CUT from bible.html between its own real boundaries (never re-typed here):
the ⟦chars-tab-js⟧ block, the Character Builder's ⟦cb-builder-js⟧ block and its ⟦CB_DB⟧ data, switchTab, the board's
LSR and both fork sets, CHARS and the Backup exporter — run together in node over a small DOM stand-in with a fake
clock, so the 5 s and 20 s windows are driven, not waited for. Every button is pressed by EVALUATING THE onclick THE
ROOM RENDERED, so a card whose button names the wrong build, or no function, is caught — not a helper called beside it.

  · THE TAB IS A ROOM OF ITS OWN, IN THE WORKSHOP, RIGHT BEFORE THE VAULT: `data-tab="chars"` sits immediately before
    `data-tab="vault"` in .tabs-workshop, its pane is a `tab-content` like its siblings, the console shell's app-ctx
    re-show list names it, and switchTab('chars') repaints it from the store.
  · THE CARDS ARE EXACTLY THE BUILDS: a seeded d2r_charBuilds of three builds renders three cards, one per build id,
    the MAIN one first with the ★ MAIN badge, the rest newest first; a card says its name, class, level, the items
    across its sets + inventory (10 slots + 2 swap = 12 worn, 3 in inventory = 15) and when it last changed.
  · SET AS MAIN writes ONLY d2r_cbMain (= that build's id) and reorders: the new MAIN leads, and only it wears the badge.
  · DELETE IS TWO STEPS IN THE PAGE: the first press writes nothing and the button reads "Confirm delete?"; after 5 s
    it is "Delete" again and a press only re-arms; a second press inside 5 s removes THAT build and no other. Undo puts
    the store back BYTE-IDENTICAL (the seed is pretty-printed, so a re-serialised store could not pass); after 20 s
    the Undo is gone and the build stays gone. Deleting the MAIN clears d2r_cbMain, and its Undo restores it. An Undo
    after another build changed puts the deleted one back at its place with its own bytes and keeps the other change.
  · THE SEPARATION, PROVEN: across every action — open, MAIN, arm, expire, delete, undo, a builder edit, + New
    character — every OTHER localStorage key (his mules, vault, owned list, chronicle, and the ladder copies) is
    byte-identical before and after; the only keys written are d2r_charBuilds / d2r_cbMain / d2r_cbSel; no vault or
    mule function is called; and the block's code names no vault or mule store or function, and no browser dialog.
  · OPEN IS THE SAME PLANNER: Open calls window.openCharBuilder with THAT build's id and the builder opens on it; a
    builder edit then close repaints the card (the room watches the builder's html.cb-lock).
  · THE BUILDER'S BUILD DROPDOWN shows the MAIN build first, marked "★ MAIN" — and nothing else about it moves.
  · UNKNOWN IS NOT EMPTY: a store that does not parse shows "UNKNOWN", no cards, disables + New character, and every
    write refuses; an empty store says "No characters yet" and offers + New character, which opens the builder's own
    new-build flow and the new build appears on close.
  · PER ACCOUNT: d2r_cbMain is in _LP_FORKED beside d2r_charBuilds; on the ladder profile MAIN lands in L·d2r_cbMain
    and main's is untouched; Backup & Share exports it under its bare name.

THE #245 REVIEW'S FIVE ROOM DEFECTS, each reproduced in headless Chrome before it was fixed, and each held here:
  · THE UNDO BAR KEEPS HIS BUTTON: it was rebuilt with innerHTML every second, so Undo was a new element each tick -
    keyboard focus gone within a second, a press straddling a tick lost, the aria-live sentence re-announced every
    second. The harness now keeps the two lists as a browser does (a replaced box loses its focused element to
    <body>), so "the same button, still focused, three ticks later" is an identity check, and the countdown still
    counts (20 -> 17) inside a span the live region ignores.
  · A KEYBOARD DELETE COMPLETES WHERE HE IS: Enter arms, focus stays on "Confirm delete?", Enter deletes and focus
    moves to that build's Undo, Enter there puts it back and focus lands on its card.
  · ONE DOUBLE-CLICK IS NOT A DELETE: a confirm 80 ms after its arm is refused (still armed, nothing written); a
    deliberate press a second later deletes.
  · UNDO IN ANY ORDER IS BYTE-IDENTICAL: first-delete-first, middle-first and last-first all end on the exact
    pretty-printed seed string.
  · NEVER UNDER THE OPEN PLANNER: with the builder open, Delete refuses (nothing armed, nothing written) and says why;
    another window's delete paints the builder's "no longer saved" state (by the storage event, by the next commit,
    and by the next render), a store that cannot be parsed reads UNKNOWN there, never "deleted".
  · AND APP CONTEXT'S ROW CAN BE REACHED: the eighth tab made the centred ?app=1 row overflow past its left edge where
    no scroll reaches (SESSIONS cut to "NS" at 375) and wrap 7+1 at 750-800. Pinned here as the two CSS rules that
    fix it; the pixels were measured in headless Chrome (375-1120), which this law cannot do.

⚠ WHAT THIS LAW CANNOT SEE: pixels (the room was looked at in headless Chrome at 2000x1300 and 375x812 when it was
built), and the CONSOLE's own header strip (tv/control_ui.html #head-tabs) - its door is pinned by the case below (2026-09-27: an icon-only 👤 chip, Tools icon-only too, measured one row at 1120/1440/1600 with the live icons stood in; 901/1000 wrap on HEAD as well) — inside
the console shell the board's tab row is hidden, so this room is reached on the website and in app context, not from
the console header. That is recorded as open work, not claimed here: a ninth header tab was built and measured in a
private console and it does NOT fit his one-row strip (v2100: "the main tabs on top should be one row") - it wrapped
to a second row at 901, 1000, 1120 (his window), 1440 and 1600, short by 99 / 6 / 106 / 55 / 25 px - so where the
door goes is his call. RED_PROOF below.
"""
import io
import json
import os
import re
import shutil
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

NODE = shutil.which("node")
BIBLE = os.path.join(ROOT, "bible.html")
ALLOWED_WRITES = {"d2r_charBuilds", "d2r_cbMain", "d2r_cbSel"}


def _src():
    with io.open(BIBLE, encoding="utf-8") as f:
        return f.read()


def _between(s, start, end):
    n = s.count(start)
    assert n == 1, "the cut start %r is not unique (%d) - the anchor moved" % (start[:60], n)
    i = s.index(start) + len(start)
    j = s.index(end, i)
    return s[i:j]


def _chars_js(s):
    return _between(s, '<script id="chars-tab-js">', "\n</script>")


def _stage(s):
    """the board pieces the room stands on, each cut between its own boundaries"""
    lp = "window._LP_FORKED = new Set([" + _between(s, "window._LP_FORKED = new Set([", "]);") + "]);\n"
    # the statement ends at its own ']));' (a comment follows on the line) - the old ');\n' marker ran on into LSR
    # and parsed by luck until LSR gained a '});' (v3525), which ended the cut mid-function
    wp = "window._WP_FORKED = new Set(" + _between(s, "window._WP_FORKED = new Set(", "]));") + "]));\n"
    lsr = "window.LSR = (function(){" + _between(s, "window.LSR = (function(){", "\n})();") + "\n})();\n"
    chars = "const CHARS = {" + _between(s, "const CHARS = {", "\n};\n") + "\n};\n"
    backup = "function _collectProgress(){" + _between(s, "function _collectProgress(){", "\nfunction _progressSnapshot(){") + "\n"
    switch = "function switchTab(name) {" + _between(s, "function switchTab(name) {", "\n}\n\n// ===== TZ TRACKER") + "\n}\n"
    builder = _between(s, '<script id="cb-builder-js">', "\n</script>")
    db = _between(s, '<script type="application/json" id="cb-db">', "</script>")
    return lp, wp, lsr, chars, backup, switch, builder, db


HARNESS = r"""
var RAW = {}, WRITES = [], CALLS = [], LISTEN = [], WLISTEN = [], MOS = [], OPENED = [];
var NOW = 1790000000000, TIMERS = [], TID = 0;
Date.now = function(){ return NOW; };
function setTimeout(f, ms){ TID++; TIMERS.push({ id: TID, at: NOW + (ms | 0), f: f, every: 0 }); return TID; }
function setInterval(f, ms){ TID++; TIMERS.push({ id: TID, at: NOW + (ms | 0), f: f, every: ms | 0 || 1 }); return TID; }
function clearTimeout(id){ TIMERS = TIMERS.filter(function(t){ return t.id !== id; }); }
var clearInterval = clearTimeout;
function advance(ms){
  var end = NOW + ms;
  for (;;){
    TIMERS.sort(function(a, b){ return a.at - b.at; });
    var t = TIMERS[0]; if (!t || t.at > end) break;
    NOW = t.at; if (t.every) t.at += t.every; else TIMERS.shift();
    t.f();
  }
  NOW = end;
}
var localStorage = {
  getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
  setItem: function(k, v){ WRITES.push(['set', k]); RAW[k] = String(v); },
  removeItem: function(k){ WRITES.push(['remove', k]); delete RAW[k]; },
  key: function(i){ var ks = Object.keys(RAW); return ks[i] == null ? null : ks[i]; }
};
Object.defineProperty(localStorage, 'length', { get: function(){ return Object.keys(RAW).length; } });
var window = globalThis;
window.localStorage = localStorage;
window._D2R_OWNER = true; window.D2R_PROFILE = __PROFILE__; window._D2R_LPFX = 'L·'; window._D2R_PFX = 'W·';
window._D2R_INSTALL = 'test';
/* the vault and the mules, as spies: nothing on this side may call them */
['vaultAssign', 'vaultAutoAssign', 'openMuleCard', 'tvVaultRegister', '_muleLoad', 'vaultCloseCard', 'muleById', 'renderVault'].forEach(function(n){
  window[n] = function(){ CALLS.push(n); };
});
/* his real stores are there, full, in both accounts: touching any of them is the defect */
RAW['d2r_muleAssign'] = '{"Harlequin Crest (Shako)":"m1","Enigma":"m2"}';
RAW['d2r_muleEquip'] = '{"m1":{"head":"Harlequin Crest"}}';
RAW['d2r_muleRoster'] = '[{"id":"m1","name":"Mule One"}]';
RAW['d2r_owned'] = '["Harlequin Crest","Enigma"]';
RAW['d2r_foundLog'] = '[{"n":"Harlequin Crest","t":1}]';
RAW['d2r_vaultRemoved'] = '[]';
RAW['d2r_vaultBackfill_v2200'] = '1';
RAW['L·d2r_owned'] = '["Griffon\'s Eye"]';
RAW['L·d2r_muleAssign'] = '{"Griffon\'s Eye":"m9"}';
RAW['d2r_cbSel'] = 'bOLD';
function Cls(onchange){ var c = {}; function ch(){ if (onchange) onchange(); }
  return { add: function(x){ var had = !!c[x]; c[x] = 1; if (!had) ch(); }, remove: function(x){ var had = !!c[x]; delete c[x]; if (had) ch(); },
    contains: function(x){ return !!c[x]; },
    toggle: function(x, on){ if (on === undefined) on = !c[x]; var had = !!c[x]; if (on) c[x] = 1; else delete c[x]; if (had !== !!on) ch(); return on; } }; }
function El(id){ this.id = id || ''; this.hidden = false; this.disabled = false; this.attrs = {}; this._html = ''; this.style = {}; this.classList = Cls();
  this.scrollTop = 0; this.children = []; this.textContent = ''; this.offsetWidth = 100; }
El.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); if (k === 'id') this.id = String(v); };
El.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
El.prototype.querySelector = function(){ return null; };
/* #245 review - the room's two lists as a browser holds them. Setting innerHTML on #chars-list / #chars-undo REPLACES
   every element in the box - one that had focus loses it to <body>, exactly as in a browser - and the new elements
   are objects with their attributes, so "the same button" is an identity question and a keyboard press (enter())
   acts on whatever holds focus. Only these two boxes are parsed; every other stand-in stays string-only. */
var PARSED = { 'chars-list': 1, 'chars-undo': 1 };
function _attrs(s){ var o = {}, re = /([\w-]+)(?:="([^"]*)")?/g, m; while ((m = re.exec(s))) o[m[1]] = m[2] == null ? '' : decode(m[2]); return o; }
El.prototype.querySelectorAll = function(sel){
  if (sel === 'button[data-act]' && this._kids) return this._kids.filter(function(k){ return k.tag === 'button' && k.attrs['data-act'] != null; });
  return [];
};
El.prototype.contains = function(x){ return !!(this._kids && this._kids.indexOf(x) >= 0); };
El.prototype.getBoundingClientRect = function(){ return { left: 0, top: 0, width: 100, height: 40, right: 100, bottom: 40 }; };
El.prototype.appendChild = function(c){ this.children.push(c); if (c.id) ELS[c.id] = c; return c; };
El.prototype.focus = function(){ if (this.tag && !this.disabled) document.activeElement = this; };
El.prototype.scrollIntoView = function(){};
Object.defineProperty(El.prototype, 'innerHTML', { get: function(){ return this._html; }, set: function(v){
  this._html = String(v);
  if (!PARSED[this.id]) return;
  this.writes = (this.writes || 0) + 1;
  if (this._kids && this._kids.indexOf(document.activeElement) >= 0) document.activeElement = document.body;
  var kids = [], re = /<([a-z]+)((?:\s+[\w-]+(?:="[^"]*")?)*)\s*>([^<]*)/g, m;
  while ((m = re.exec(this._html))){
    var e = new El(''); e.tag = m[1]; e.attrs = _attrs(m[2]); e.disabled = Object.prototype.hasOwnProperty.call(e.attrs, 'disabled');
    e.textContent = decode(m[3]);
    if (e.attrs.id){ e.id = e.attrs.id; ELS[e.id] = e; }
    kids.push(e);
  }
  this._kids = kids;
} });
var ELS = {}, MODAL = new El('cb-modal'), TABBTN = {};
['chars-list', 'chars-undo', 'chars-say', 'chars-new', 'tab-chars', 'tab-vault'].forEach(function(id){ ELS[id] = new El(id); });
var DBEL = new El('cb-db'); DBEL.textContent = __DB__;
function MutationObserver(cb){ this.cb = cb; }
MutationObserver.prototype.observe = function(t, o){ MOS.push({ t: t, cb: this.cb, o: o }); };
var HTML = new El('html');
HTML.classList = Cls(function(){ MOS.forEach(function(m){ if (m.t === HTML) m.cb([{ type: 'attributes', attributeName: 'class' }]); }); });
var document = {
  body: new El('body'), documentElement: HTML, activeElement: null, readyState: 'complete',
  getElementById: function(id){
    if (id === 'cb-db') return DBEL;
    if (id === 'cb-modal') return (ELS['cb-win'] && ELS['cb-win']._html.indexOf('id="cb-modal"') >= 0) ? MODAL : null;
    return ELS[id] || null;
  },
  createElement: function(){ return new El(''); },
  querySelector: function(sel){ var m = /^\.tab\[data-tab="(\w+)"\]$/.exec(sel); if (m){ if (!TABBTN[m[1]]) TABBTN[m[1]] = new El('btn-' + m[1]); return TABBTN[m[1]]; } return null; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(t, f, cap){ LISTEN.push([t, f, !!cap]); }
};
document.body.appendChild = function(c){ if (c.id) ELS[c.id] = c; return c; };
window.document = document;
window.addEventListener = function(t, f){ WLISTEN.push([t, f]); };
window.innerWidth = 2000; window.innerHeight = 1300; window.scrollY = 0;
var sessionStorage = { getItem: function(){ return null; }, setItem: function(){} };
var activeItem = null;
function $(id){ return document.getElementById(id); }
function artOr(n){ return '<span class="d2art-wrap">' + n + '</span>'; }
function decode(s){ return String(s).replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); }
/* the room as rendered: cards in order, each with its badge and its buttons (label, onclick, disabled) */
function cards(){
  var out = [], re = /<article class="chx-card( chx-main)?" data-build="([^"]*)">([\s\S]*?)<\/article>/g, m;
  while ((m = re.exec(ELS['chars-list']._html))){
    var btns = {}, bre = /<button([^>]*)>([^<]*)<\/button>/g, b;
    while ((b = bre.exec(m[3]))){
      var a = /data-act="(\w+)"/.exec(b[1]), oc = /onclick="([^"]*)"/.exec(b[1]);
      if (a) btns[a[1]] = { label: b[2], onclick: oc ? decode(oc[1]) : null, disabled: / disabled/.test(b[1]) };
    }
    out.push({ id: decode(m[2]), main: !!m[1], badge: /data-main="1"/.test(m[3]), html: m[3], btns: btns });
  }
  return out;
}
function ids(){ return cards().map(function(c){ return c.id; }); }
function card(id){ var c = null; cards().forEach(function(x){ if (x.id === id) c = x; }); return c; }
/* press a button the room rendered, by evaluating ITS onclick */
function press(id, act){
  var c = card(id); if (!c) return 'no-card';
  var b = c.btns[act]; if (!b) return 'no-button';
  if (b.disabled || !b.onclick) return 'disabled';
  return (new Function('return (' + b.onclick + ');'))();
}
function pressUndo(id){
  var re = /<div class="chx-undo-row" data-undo="([^"]*)">[\s\S]*?onclick="([^"]*)"/g, m, oc = null;
  while ((m = re.exec(ELS['chars-undo']._html))) if (decode(m[1]) === id) oc = decode(m[2]);
  if (!oc) return 'no-undo';
  return (new Function('return (' + oc + ');'))();
}
/* the parsed lists: a button by action + build, what holds focus, a keyboard Enter on it, an undo row's seconds */
function kids(box, pred){ return (ELS[box]._kids || []).filter(pred); }
function btn(box, act, id){ var k = kids(box, function(e){ return e.tag === 'button' && e.attrs['data-act'] === act && e.attrs['data-for'] === id; }); return k.length === 1 ? k[0] : null; }
function focused(){ var a = document.activeElement; if (a === document.body) return 'BODY'; if (!a || !a.tag) return null; return [a.attrs['data-act'] || null, a.attrs['data-for'] == null ? null : a.attrs['data-for'], a.textContent]; }
function enter(){ var a = document.activeElement; if (!a || a.tag !== 'button' || a.disabled || a.attrs.onclick == null) return 'no-focused-button'; return (new Function('return (' + a.attrs.onclick + ');'))(); }
function secs(id){ var ks = ELS['chars-undo']._kids || [], on = false; for (var i = 0; i < ks.length; i++){ if (ks[i].attrs['data-undo'] != null) on = ks[i].attrs['data-undo'] === id; else if (on && /^chars-undo-s-/.test(ks[i].id)) return ks[i].textContent; } return null; }
function undoRows(){ return kids('chars-undo', function(e){ return e.attrs['data-undo'] != null; }).map(function(e){ return e.attrs['data-undo']; }); }
/* a deliberate two-step delete: arm, a second later confirm (a confirm inside CONFIRM_MIN_MS is a double-click) */
function del(id){ var a = press(id, 'del'); advance(1000); var b = press(id, 'del'); return a + '/' + b; }
function others(){ var o = {}; Object.keys(RAW).sort().forEach(function(k){ var bare = k.replace(/^L·/, ''); if (!/^(d2r_charBuilds|d2r_cbMain|d2r_cbSel)$/.test(bare)) o[k] = RAW[k]; }); return JSON.stringify(o); }
function b(name, cls, level, at, sets){ return { name: name, cls: cls, level: level, sets: sets, active: 0, notes: '', stash: [], from: null, at: at }; }
function set1(slots, inv, swap){ return { name: 'Set 1', slots: slots || {}, inv: inv || [], swap: swap || {}, ws: 1 }; }
var HAMMER = b('Hammerdin', 'Paladin', 92, NOW - 3 * 3600000, [set1(
  { head: { name: 'Harlequin Crest' }, tors: { name: 'Enigma' }, rarm: { name: 'Heart of the Oak' }, larm: { name: 'Herald of Zakarum' },
    rrin: { name: 'Stone of Jordan' }, lrin: { name: 'Bul-Kathos\' Wedding Band' }, neck: { name: 'Mara\'s Kaleidoscope' },
    belt: { name: 'Arachnid Mesh' }, feet: { name: 'Sandstorm Trek' }, glov: { name: 'Magefist' } },
  [{ name: 'Annihilus', x: 0, y: 0, w: 1, h: 1 }, { name: 'Hellfire Torch', x: 1, y: 0, w: 1, h: 3 }, { name: 'Grand Charm', x: 2, y: 0, w: 1, h: 3 }],
  { rarm: { name: 'Call to Arms' }, larm: { name: 'Spirit' } })]);
var SORC = b('Blizz Sorc', 'Sorceress', 85, NOW - 40 * 60000, [set1({ head: { name: 'Harlequin Crest' } }), set1({}, [{ name: 'Annihilus', x: 0, y: 0, w: 1, h: 1 }])]);
var DRUID = b('Druid build', null, 1, NOW - 9 * 86400000, [set1()]);
function seed(main){
  var all = { bHAM: HAMMER, bSORC: SORC, bDRU: DRUID };
  window.LSR.setItem('d2r_charBuilds', JSON.stringify(all, null, 1));     /* pretty: a re-serialised store cannot pass as byte-identical */
  if (main) window.LSR.setItem('d2r_cbMain', main);
  WRITES.length = 0;
}
"""


def _run(body, profile="main", raw_patch=None):
    s = _src()
    lp, wp, lsr, chars, backup, switch, builder, db = _stage(s)
    prog = (HARNESS.replace("__DB__", json.dumps(db)).replace("__PROFILE__", json.dumps(profile))
            + lp + wp + lsr + chars + backup + switch
            + ("\n" + raw_patch + "\n" if raw_patch else "")
            + builder + "\n"
            + "var _realOpen = window.openCharBuilder; window.openCharBuilder = function(id){ OPENED.push(id === undefined ? '(none)' : id); return _realOpen.apply(this, arguments); };\n"
            + _chars_js(s)
            + "\n;(function(){ var OUT = {};\n" + body
            + "\nprocess.stdout.write(JSON.stringify(OUT)); })();\n")
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout)


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheCharactersTabIsManualAndSeparate(unittest.TestCase):

    def test_the_console_header_has_a_characters_door(self):
        """his answer 2026-09-26: 'the character build tool gets its own tab up top' - in HIS console too."""
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        i = ui.index('id="head-tabs"'); nav = ui[i:ui.index("</nav>", i)]
        doors = re.findall(r'<button class="ht[^"]*"[^>]*data-tab="chars"[^>]*>.*?</button>', nav, flags=re.S)
        self.assertEqual(len(doors), 1, "the console header has %d Characters door(s), not one" % len(doors))
        self.assertIn('class="ht-lbl">Characters</span>', doors[0], "the door has no name for a screen reader")
        self.assertIn("ht-icon", doors[0], "the door is a full-width tab: the one-row header (his v2100 rule) wraps")
        order = re.findall(r'data-tab="([a-z]+)"', nav)
        self.assertEqual(order.index("chars") + 1, order.index("vault"), "the Characters door does not sit right before Vault")


    def test_the_tab_is_a_room_of_its_own_right_before_the_vault(self):
        s = _src()
        ws = re.search(r'<div class="tabs-workshop"(.*?)</div>', s, re.S)
        self.assertIsNotNone(ws, "the .tabs-workshop row is gone")
        order = re.findall(r'<button class="tab" data-tab="([a-z0-9]+)"', ws.group(1))
        self.assertIn("chars", order, "the Characters tab is not in the WORKSHOP cluster: %s" % order)
        self.assertIn("vault", order)
        self.assertEqual(order.index("chars") + 1, order.index("vault"),
                         "the Characters tab must sit right before the Vault: %s" % order)
        btn = re.search(r'<button class="tab" data-tab="chars">([^<]*)</button>', s)
        self.assertIn("Characters", btn.group(1))
        self.assertEqual(s.count('id="tab-chars"'), 1, "the Characters pane must exist exactly once")
        panes = dict((t, c) for c, t in re.findall(r'<div class="([a-z-]+)" id="tab-([a-z0-9]+)">', s))
        self.assertEqual(panes.get("chars"), panes.get("vault"),
                         "the Characters pane uses %r while its sibling uses %r - a pane with the wrong class never hides"
                         % (panes.get("chars"), panes.get("vault")))
        blk = _between(s, 'body.app-ctx .tabs .tab[data-tab="session"]', "display:inline-flex")
        self.assertIn('data-tab="chars"', blk, "app context hides every tab it does not re-show by name")
        what = re.search(r'id="chars-what">([^<]*)<', s)
        self.assertIsNotNone(what, "the line saying what this tab is and is not is gone")
        # #103 (his ruling 2026-09-30) - the room now also shows the characters his reels learned, in their own section;
        # the Vault's separation is unchanged: nothing a reader VAULTS lands here
        # v3855 item C (his ruling): one short line says what the room does
        self.assertEqual(what.group(1), "Automatically syncs your items to characters")
        out = _run(r"""
          seed('bSORC');
          window.renderCharsTab(); OUT.before = ids();
          /* another writer changes the store; entering the room must show it */
          var all = JSON.parse(RAW['d2r_charBuilds']); delete all.bDRU; RAW['d2r_charBuilds'] = JSON.stringify(all);
          switchTab('chars'); OUT.after = ids(); OUT.active = ELS['tab-chars'].classList.contains('active');
        """)
        self.assertEqual(out["before"], ["bSORC", "bHAM", "bDRU"])
        self.assertEqual(out["after"], ["bSORC", "bHAM"], "switchTab('chars') did not repaint the room from the store")
        self.assertTrue(out["active"])

    def test_the_cards_are_exactly_the_builds_main_first(self):
        out = _run(r"""
          seed('bDRU');
          window.renderCharsTab();
          OUT.ids = ids(); OUT.main = cards().map(function(c){ return [c.id, c.main, c.badge]; });
          var h = card('bHAM').html;
          OUT.ham = { name: /Hammerdin/.test(h), cls: /Paladin · level 92/.test(h), items: /<b>15<\/b> items/.test(h),
                      worn: /12 worn/.test(h), inv: /3 in inventory/.test(h), sets: /1 set</.test(h), when: /changed 3 h ago/.test(h) };
          var d = card('bDRU').html; OUT.druCls = /class UNKNOWN/.test(d); OUT.druItems = /<b>0<\/b> items/.test(d);
          OUT.labels = card('bHAM').btns;
          OUT.mainBtn = card('bDRU').btns.main;
        """)
        self.assertEqual(out["ids"], ["bDRU", "bSORC", "bHAM"], "MAIN first, then newest first: %s" % out["ids"])
        self.assertEqual(out["main"], [["bDRU", True, True], ["bSORC", False, False], ["bHAM", False, False]])
        self.assertEqual(out["ham"], {"name": True, "cls": True, "items": True, "worn": True, "inv": True,
                                      "sets": True, "when": True}, "a card must say what the build is")
        self.assertTrue(out["druCls"], "a build with no class must say class UNKNOWN")
        self.assertTrue(out["druItems"])
        self.assertEqual(out["labels"]["open"]["label"], "Open")
        self.assertEqual(out["labels"]["main"]["label"], "★ Set as MAIN")
        self.assertEqual(out["labels"]["del"]["label"], "Delete")
        self.assertTrue(out["mainBtn"]["disabled"], "the MAIN card offers Set as MAIN again")

    def test_set_as_main_writes_only_the_main_key_and_reorders(self):
        out = _run(r"""
          seed('bDRU'); window.renderCharsTab();
          var before = others(), builds = RAW['d2r_charBuilds'];
          OUT.r = press('bHAM', 'main');
          OUT.writes = WRITES.slice(); OUT.main = RAW['d2r_cbMain']; OUT.ids = ids();
          OUT.badges = cards().filter(function(c){ return c.badge; }).map(function(c){ return c.id; });
          OUT.othersSame = others() === before; OUT.buildsSame = RAW['d2r_charBuilds'] === builds;
        """)
        self.assertTrue(out["r"])
        self.assertEqual(out["writes"], [["set", "d2r_cbMain"]], "Set as MAIN wrote more than d2r_cbMain: %s" % out["writes"])
        self.assertEqual(out["main"], "bHAM")
        self.assertEqual(out["ids"], ["bHAM", "bSORC", "bDRU"])
        self.assertEqual(out["badges"], ["bHAM"], "one MAIN at a time")
        self.assertTrue(out["othersSame"])
        self.assertTrue(out["buildsSame"], "Set as MAIN rewrote the builds")

    def test_delete_is_two_steps_and_undo_is_byte_identical(self):
        out = _run(r"""
          seed(null); window.renderCharsTab();
          var raw0 = RAW['d2r_charBuilds'], before = others();
          OUT.p1 = press('bSORC', 'del'); OUT.w1 = WRITES.length; OUT.lab1 = card('bSORC').btns.del.label;
          OUT.labOther = card('bHAM').btns.del.label;
          advance(5001); OUT.lab2 = card('bSORC').btns.del.label;
          OUT.p2 = press('bSORC', 'del'); OUT.w2 = WRITES.length;          /* a press after the window only re-arms */
          advance(2000);
          OUT.p3 = press('bSORC', 'del');                                   /* the confirm, inside the window */
          OUT.idsAfter = ids(); OUT.writes = WRITES.slice();
          var left = JSON.parse(RAW['d2r_charBuilds']); OUT.left = Object.keys(left);
          OUT.hamSame = JSON.stringify(left.bHAM) === JSON.stringify(JSON.parse(raw0).bHAM);
          OUT.undoShown = !ELS['chars-undo'].hidden && /Deleted <b>Blizz Sorc<\/b>/.test(ELS['chars-undo']._html);
          advance(12000);
          OUT.u = pressUndo('bSORC');
          OUT.byteSame = RAW['d2r_charBuilds'] === raw0; OUT.idsBack = ids(); OUT.undoGone = ELS['chars-undo'].hidden;
          /* and a delete that is NOT undone inside 20 s stays done */
          del('bDRU');
          var after = RAW['d2r_charBuilds'];
          advance(20001);
          OUT.expiredBar = ELS['chars-undo'].hidden; OUT.lateUndo = pressUndo('bDRU'); OUT.lateCall = window._charsUndo('bDRU');
          OUT.stillGone = RAW['d2r_charBuilds'] === after && ids().indexOf('bDRU') < 0;
          OUT.othersSame = others() === before; OUT.calls = CALLS;
        """)
        self.assertEqual(out["p1"], "armed")
        self.assertEqual(out["w1"], 0, "the first press wrote to storage - delete must be two steps")
        self.assertEqual(out["lab1"], "Confirm delete?")
        self.assertEqual(out["labOther"], "Delete", "arming one card armed another")
        self.assertEqual(out["lab2"], "Delete", "the confirm did not lapse after 5 s")
        self.assertEqual(out["p2"], "armed")
        self.assertEqual(out["w2"], 0, "a press after the 5 s window deleted without a confirm")
        self.assertEqual(out["p3"], "deleted")
        self.assertEqual(out["writes"], [["set", "d2r_charBuilds"]], "the delete wrote more than the builds: %s" % out["writes"])
        self.assertEqual(sorted(out["left"]), ["bDRU", "bHAM"], "the delete removed more (or less) than that one build")
        self.assertTrue(out["hamSame"], "the delete changed a build it did not name")
        self.assertTrue(out["undoShown"], "no Undo bar after the delete")
        self.assertTrue(out["u"])
        self.assertTrue(out["byteSame"], "Undo did not restore the store byte-identical")
        self.assertEqual(out["idsBack"], ["bSORC", "bHAM", "bDRU"])
        self.assertTrue(out["undoGone"])
        self.assertTrue(out["expiredBar"], "the Undo bar outlived its 20 s")
        self.assertEqual(out["lateUndo"], "no-undo")
        self.assertFalse(out["lateCall"], "an Undo still worked after 20 s")
        self.assertTrue(out["stillGone"])
        self.assertTrue(out["othersSame"], "a delete / undo changed a store that is not the builds'")
        self.assertEqual(out["calls"], [])

    def test_deleting_the_main_clears_it_and_undo_restores_it(self):
        out = _run(r"""
          seed('bHAM'); window.renderCharsTab();
          var raw0 = RAW['d2r_charBuilds'];
          press('bHAM', 'del'); advance(1000); OUT.r = press('bHAM', 'del');
          OUT.mainGone = !Object.prototype.hasOwnProperty.call(RAW, 'd2r_cbMain'); OUT.badges = cards().filter(function(c){ return c.badge; }).length;
          OUT.bar = /it was your MAIN/.test(ELS['chars-undo']._html);
          pressUndo('bHAM');
          OUT.main = RAW['d2r_cbMain']; OUT.byteSame = RAW['d2r_charBuilds'] === raw0; OUT.first = ids()[0];
          /* an Undo after ANOTHER build changed: the deleted one returns at its place, bytes intact, the other change kept */
          del('bSORC');
          var mid = JSON.parse(RAW['d2r_charBuilds']); mid.bDRU.level = 50; mid.bDRU.at = NOW; RAW['d2r_charBuilds'] = JSON.stringify(mid);
          pressUndo('bSORC');
          var fin = JSON.parse(RAW['d2r_charBuilds']);
          OUT.order = Object.keys(fin); OUT.sorcSame = JSON.stringify(fin.bSORC) === JSON.stringify(JSON.parse(raw0).bSORC);
          OUT.druKept = fin.bDRU.level;
        """)
        self.assertEqual(out["r"], "deleted")
        self.assertTrue(out["mainGone"], "deleting the MAIN left d2r_cbMain pointing at nothing")
        self.assertEqual(out["badges"], 0)
        self.assertTrue(out["bar"])
        self.assertEqual(out["main"], "bHAM", "Undo of the MAIN did not restore d2r_cbMain")
        self.assertTrue(out["byteSame"])
        self.assertEqual(out["first"], "bHAM")
        self.assertEqual(out["order"], ["bHAM", "bSORC", "bDRU"], "the build did not return to its own place")
        self.assertTrue(out["sorcSame"], "the restored build's bytes changed")
        self.assertEqual(out["druKept"], 50, "Undo threw away a change made after the delete")

    def test_open_is_the_same_planner_and_nothing_else_is_touched(self):
        out = _run(r"""
          seed('bSORC'); window.renderCharsTab();
          var before = others();
          OUT.r = press('bHAM', 'open');
          OUT.opened = OPENED.slice(); OUT.bid = window._cbState().bid; OUT.winUp = !!ELS['cb-win'] && !ELS['cb-win'].hidden;
          var sel = /<select class="cb-sel" id="cb-build"[^>]*>([\s\S]*?)<\/select>/.exec(ELS['cb-win']._html);
          OUT.opts = sel ? (sel[1].match(/<option value="b\w+"[^>]*>[^<]*<\/option>/g) || []).map(function(o){ return decode(o.replace(/<[^>]+>/g, '')); }) : null;
          /* a builder edit, then close: the room repaints on the builder's close */
          window._cbSetField('level', 77);
          window.closeCharBuilder();
          OUT.hamLvl = /Paladin · level 77/.test(card('bHAM').html); OUT.ids = ids();
          /* + New character: the builder's own new-build flow; the new build shows once the builder closes */
          OUT.n = window._charsNew(); OUT.newOpen = !!window._cbState().newb;
          window._cbNewCls('Necromancer'); window._cbNewGo(); window.closeCharBuilder();
          OUT.count = ids().length;
          OUT.writes = WRITES.map(function(w){ return w[1]; }).filter(function(k, i, a){ return a.indexOf(k) === i; }).sort();
          OUT.othersSame = others() === before; OUT.calls = CALLS;
        """)
        self.assertEqual(out["opened"][0], "bHAM", "Open did not call openCharBuilder with that build's id")
        self.assertEqual(out["bid"], "bHAM", "the planner did not open on that build")
        self.assertTrue(out["winUp"])
        self.assertIsNotNone(out["opts"], "the builder's build dropdown is gone")
        self.assertTrue(out["opts"][0].startswith("★ MAIN · Blizz Sorc"), "the builder's dropdown must lead with the MAIN: %s" % out["opts"])
        self.assertEqual(sum(1 for o in out["opts"] if "★ MAIN" in o), 1)
        self.assertEqual([o.split(" — ")[0] for o in out["opts"][1:]], ["Hammerdin", "Druid build"],
                         "the rest of the dropdown must stay newest first")
        self.assertTrue(out["hamLvl"], "the card did not repaint when the builder closed")
        self.assertEqual(out["ids"][0], "bSORC")
        self.assertTrue(out["n"]); self.assertTrue(out["newOpen"], "+ New character did not open the builder's new-build flow")
        self.assertEqual(out["count"], 4)
        self.assertTrue(set(out["writes"]) <= ALLOWED_WRITES, "the manual side wrote %s" % out["writes"])
        self.assertTrue(out["othersSame"], "a builder session from the Characters tab changed a vault / mule store")
        self.assertEqual(out["calls"], [], "the Characters side called the vault / the mules: %s" % out["calls"])

    def test_an_unreadable_store_is_unknown_and_an_empty_one_is_empty(self):
        out = _run(r"""
          RAW['d2r_charBuilds'] = '{"bHAM": {"name": "Hammer'; WRITES.length = 0;
          window.renderCharsTab();
          OUT.state = /data-state="unknown"/.test(ELS['chars-list']._html) && /UNKNOWN/.test(ELS['chars-list']._html);
          OUT.cards = ids().length; OUT.newOff = ELS['chars-new'].disabled;
          OUT.del = window._charsDelete('bHAM'); OUT.main = window._charsSetMain('bHAM'); OUT.nw = window._charsNew();
          OUT.writes = WRITES.length; OUT.opened = OPENED.length;
          delete RAW['d2r_charBuilds']; window.renderCharsTab();
          OUT.empty = /data-state="empty"/.test(ELS['chars-list']._html) && /No characters yet/.test(ELS['chars-list']._html);
          OUT.emptyNew = /onclick="window\._charsNew\(\)"/.test(ELS['chars-list']._html); OUT.newOn = !ELS['chars-new'].disabled;
        """)
        self.assertTrue(out["state"], "an unparseable store must read UNKNOWN, never 'no characters'")
        self.assertEqual(out["cards"], 0)
        self.assertTrue(out["newOff"])
        self.assertFalse(out["del"]); self.assertFalse(out["main"]); self.assertFalse(out["nw"])
        self.assertEqual(out["writes"], 0, "a write went through on a store that could not be read")
        self.assertEqual(out["opened"], 0)
        self.assertTrue(out["empty"], "an empty store must say so")
        self.assertTrue(out["emptyNew"], "the empty state must offer + New character")
        self.assertTrue(out["newOn"])

    def test_main_forks_per_account_and_rides_backup(self):
        out = _run(r"""
          seed('bHAM'); var mainMain = RAW['d2r_cbMain'];
          window.renderCharsTab(); press('bSORC', 'main');
          OUT.keys = Object.keys(RAW).filter(function(k){ return /cbMain/.test(k); }).sort();
          OUT.ladder = RAW['L·d2r_cbMain']; OUT.mainUntouched = RAW['d2r_cbMain'] === mainMain;
          OUT.forked = window._LP_FORKED.has('d2r_cbMain') && window._WP_FORKED.has('d2r_cbMain');
          OUT.backup = _collectProgress()['d2r_cbMain'];
        """, profile="ladder", raw_patch="RAW['d2r_cbMain'] = 'bMAINWORLD';")
        self.assertTrue(out["forked"], "d2r_cbMain is not forked like d2r_charBuilds")
        self.assertEqual(out["keys"], ["L·d2r_cbMain", "d2r_cbMain"])
        self.assertEqual(out["ladder"], "bSORC")
        self.assertTrue(out["mainUntouched"], "a ladder MAIN overwrote the main account's")
        self.assertEqual(out["backup"], "bSORC", "Backup & Share must carry the active account's MAIN, bare-named")

    def test_the_undo_bar_keeps_his_button_while_it_counts_down(self):
        out = _run(r"""
          seed(null); window.renderCharsTab();
          OUT.d = del('bSORC');
          var u0 = btn('chars-undo', 'undo', 'bSORC'); OUT.u0 = !!u0; u0.focus();
          var w0 = ELS['chars-undo'].writes, s0 = secs('bSORC');
          advance(3000);                                               /* three ticks of the countdown */
          OUT.tick = { same: btn('chars-undo', 'undo', 'bSORC') === u0, focus: document.activeElement === u0,
                       barWrites: ELS['chars-undo'].writes - w0, secs: [s0, secs('bSORC')] };
          press('bHAM', 'del'); advance(5001);                         /* another card's confirm lapses: the room repaints */
          OUT.repaint = { same: btn('chars-undo', 'undo', 'bSORC') === u0, focus: document.activeElement === u0,
                          barWrites: ELS['chars-undo'].writes - w0 };
          OUT.quietSecs = /<span aria-hidden="true"> for <span id="chars-undo-s-\d+">\d+<\/span> s<\/span>/.test(ELS['chars-undo']._html);
          OUT.name = u0.attrs['aria-label'];
          OUT.enter = enter(); OUT.back = ids().indexOf('bSORC') >= 0;
        """)
        self.assertEqual(out["d"], "armed/deleted")
        self.assertTrue(out["u0"], "no Undo button for the deleted build")
        self.assertEqual(out["tick"], {"same": True, "focus": True, "barWrites": 0, "secs": ["20", "17"]},
                         "the countdown replaced the Undo button (or its focus) - a keyboard Enter or a slow click "
                         "on Undo is lost within a second: %s" % out["tick"])
        self.assertEqual(out["repaint"], {"same": True, "focus": True, "barWrites": 0},
                         "a repaint of the room took the Undo button he is on: %s" % out["repaint"])
        self.assertTrue(out["quietSecs"], "the seconds are not inside an aria-hidden span - the polite live region "
                        "re-announces the bar every second for 20 s")
        self.assertIn("20 s", out["name"], "the Undo button's own name must carry the window the hidden seconds show")
        self.assertTrue(out["enter"]); self.assertTrue(out["back"], "Enter on the focused Undo did not put the build back")

    def test_a_keyboard_delete_completes_where_he_is(self):
        out = _run(r"""
          seed(null); window.renderCharsTab();
          btn('chars-list', 'del', 'bDRU').focus(); OUT.f0 = focused();
          OUT.e1 = enter(); OUT.f1 = focused();
          advance(1000); OUT.e2 = enter(); OUT.f2 = focused(); OUT.left = ids();
          OUT.e3 = enter(); OUT.f3 = focused(); OUT.back = ids();
          btn('chars-list', 'main', 'bHAM').focus(); OUT.e4 = enter(); OUT.f4 = focused(); OUT.main = RAW['d2r_cbMain'];
        """)
        self.assertEqual(out["f0"], ["del", "bDRU", "Delete"])
        self.assertEqual(out["e1"], "armed")
        self.assertEqual(out["f1"], ["del", "bDRU", "Confirm delete?"],
                         "arming repainted the list and dropped his focus: %s" % (out["f1"],))
        self.assertEqual(out["e2"], "deleted", "a second Enter on the armed button did not delete")
        self.assertEqual(out["f2"], ["undo", "bDRU", "Undo"], "after the delete, focus must be on that build's Undo: %s" % (out["f2"],))
        self.assertEqual(out["left"], ["bSORC", "bHAM"])
        self.assertTrue(out["e3"]); self.assertIn("bDRU", out["back"])
        self.assertEqual(out["f3"], ["open", "bDRU", "Open"], "after Undo, focus must land on the restored card: %s" % (out["f3"],))
        self.assertTrue(out["e4"]); self.assertEqual(out["main"], "bHAM")
        self.assertEqual(out["f4"], ["open", "bHAM", "Open"],
                         "Set as MAIN disables itself, so focus must move to that card's Open, not to <body>: %s" % (out["f4"],))

    def test_one_double_click_is_not_a_delete(self):
        out = _run(r"""
          seed(null); window.renderCharsTab(); var raw0 = RAW['d2r_charBuilds'];
          OUT.c1 = press('bDRU', 'del'); advance(80); OUT.c2 = press('bDRU', 'del');
          OUT.kept = RAW['d2r_charBuilds'] === raw0 && ids().indexOf('bDRU') >= 0; OUT.writes = WRITES.length;
          OUT.label = card('bDRU').btns.del.label;
          advance(1000); OUT.c3 = press('bDRU', 'del'); OUT.gone = ids().indexOf('bDRU') < 0;
        """)
        self.assertEqual([out["c1"], out["c2"]], ["armed", "armed"],
                         "the second click of one double-click confirmed the delete")
        self.assertTrue(out["kept"]); self.assertEqual(out["writes"], 0)
        self.assertEqual(out["label"], "Confirm delete?", "the refused confirm must leave it armed, not disarm it")
        self.assertEqual(out["c3"], "deleted"); self.assertTrue(out["gone"])

    def test_undo_in_any_order_puts_back_the_exact_bytes(self):
        out = _run(r"""
          seed('bHAM'); window.renderCharsTab(); var raw0 = RAW['d2r_charBuilds'];
          del('bSORC'); del('bDRU'); OUT.rows = undoRows();
          pressUndo('bSORC'); pressUndo('bDRU');                        /* in the order the bar lists them */
          OUT.firstFirst = RAW['d2r_charBuilds'] === raw0; OUT.order1 = Object.keys(JSON.parse(RAW['d2r_charBuilds']));
          del('bHAM'); del('bSORC'); del('bDRU');
          pressUndo('bSORC'); pressUndo('bHAM'); pressUndo('bDRU');     /* the middle one first */
          OUT.middleFirst = RAW['d2r_charBuilds'] === raw0; OUT.main = RAW['d2r_cbMain'];
          del('bSORC'); del('bDRU'); pressUndo('bDRU'); pressUndo('bSORC');
          OUT.lastFirst = RAW['d2r_charBuilds'] === raw0; OUT.ids = ids();
        """)
        self.assertEqual(out["rows"], ["bSORC", "bDRU"])
        self.assertEqual(out["order1"], ["bHAM", "bSORC", "bDRU"], "undone first-delete-first, a build came back out of place")
        self.assertTrue(out["firstFirst"], "undone in the bar's order, the store is not the string it was")
        self.assertTrue(out["middleFirst"], "three deletes, the middle undone first: the store is not the string it was")
        self.assertEqual(out["main"], "bHAM")
        self.assertTrue(out["lastFirst"])
        self.assertEqual(out["ids"], ["bHAM", "bSORC", "bDRU"])

    def test_a_build_open_in_the_planner_is_never_deleted_under_it(self):
        out = _run(r"""
          seed(null); window.renderCharsTab(); var raw0 = RAW['d2r_charBuilds'];
          press('bHAM', 'open'); OUT.lock = HTML.classList.contains('cb-lock');
          OUT.d = [press('bHAM', 'del'), (advance(1000), press('bHAM', 'del')), press('bSORC', 'del')];
          OUT.kept = RAW['d2r_charBuilds'] === raw0; OUT.label = card('bHAM').btns.del.label;
          OUT.say = ELS['chars-say'].hidden ? '' : ELS['chars-say'].textContent;
          /* another window deletes the build the planner is on: its storage event is the only word of it */
          var all = JSON.parse(RAW['d2r_charBuilds']); delete all.bHAM; RAW['d2r_charBuilds'] = JSON.stringify(all);
          WLISTEN.forEach(function(l){ if (l[0] === 'storage') l[1]({ key: 'd2r_charBuilds' }); });
          OUT.byEvent = /data-state="gone"/.test(ELS['cb-win']._html) && /no longer saved/.test(ELS['cb-win']._html);
          window._cbSetField('level', 50); window._cbSwap(2);
          OUT.stillGone = !Object.prototype.hasOwnProperty.call(JSON.parse(RAW['d2r_charBuilds']), 'bHAM');
          window.closeCharBuilder(); OUT.sayAfter = ELS['chars-say'].hidden;
          /* the same build vanishing with NO event (a writer this window never hears): the next commit says so ... */
          press('bSORC', 'open'); all = JSON.parse(RAW['d2r_charBuilds']); delete all.bSORC; RAW['d2r_charBuilds'] = JSON.stringify(all);
          window._cbNotes('a note');
          OUT.byCommit = /data-state="gone"/.test(ELS['cb-win']._html);
          OUT.noteKept = RAW['d2r_charBuilds'].indexOf('a note') < 0 && RAW['d2r_charBuilds'].indexOf('"bSORC"') < 0;
          window.closeCharBuilder();
          /* ... and so does the next render */
          press('bDRU', 'open'); all = JSON.parse(RAW['d2r_charBuilds']); delete all.bDRU; RAW['d2r_charBuilds'] = JSON.stringify(all);
          window._cbView('calc');
          OUT.byRender = /data-state="gone"/.test(ELS['cb-win']._html);
          window.closeCharBuilder();
          /* an unreadable store is UNKNOWN in the planner, never "deleted" */
          seed(null); window.renderCharsTab(); press('bHAM', 'open'); RAW['d2r_charBuilds'] = '{"bHAM": ';
          WLISTEN.forEach(function(l){ if (l[0] === 'storage') l[1]({ key: 'd2r_charBuilds' }); });
          OUT.unknown = /UNKNOWN/.test(ELS['cb-win']._html) && !/no longer saved/.test(ELS['cb-win']._html);
          window.closeCharBuilder();
          /* closed: the room deletes again */
          seed(null); window.renderCharsTab(); OUT.after = del('bSORC');
          OUT.calls = CALLS;
        """)
        self.assertTrue(out["lock"])
        self.assertEqual(out["d"], ["builder-open", "builder-open", "builder-open"],
                         "the room armed or deleted a build while the planner was open over it: %s" % out["d"])
        self.assertTrue(out["kept"]); self.assertEqual(out["label"], "Delete")
        self.assertIn("Character Builder is open", out["say"])
        self.assertTrue(out["byEvent"], "another window deleted the build on screen and the planner kept showing it")
        self.assertTrue(out["stillGone"], "an edit in the planner brought a deleted build back")
        self.assertTrue(out["sayAfter"], "the room still says the planner is open after it closed")
        self.assertTrue(out["byCommit"], "an edit to a build that is no longer saved was dropped in silence")
        self.assertTrue(out["noteKept"])
        self.assertTrue(out["byRender"], "the planner rendered nothing and left the stale build on screen")
        self.assertTrue(out["unknown"], "an unreadable store must read UNKNOWN in the planner, never 'deleted'")
        self.assertEqual(out["after"], "armed/deleted")
        self.assertEqual(out["calls"], [])

    def test_app_context_row_starts_where_a_scroll_can_reach(self):
        s = _src()
        i = s.index('body.app-ctx .tabs .tab{display:none}')
        blk = s[i:s.index("</style>", i)]
        code = re.sub(r"/\*.{0,6000}?\*/", " ", blk, flags=re.S)
        self.assertGreater(len(code), 1500, "the comment strip ate the app-context block - measure the real thing")
        self.assertEqual(code.count("body.app-ctx .tabs{justify-content:flex-start !important}"), 1,
                         "app context's tab row is centred by justify-content again: a row wider than the bar "
                         "overflows past its LEFT edge, where no scroll reaches (SESSIONS read 'NS' at 375)")
        self.assertEqual(code.count("body.app-ctx .tabs .tabs-workshop{margin-left:auto !important;margin-right:auto !important}"), 1,
                         "the row that fits is no longer centred by the workshop's own auto margins")
        m = re.search(r"@media \(min-width:701px\) and \(max-width:(\d+)px\)\{\s*body\.app-ctx:not\(\.engine-driven\) "
                      r"\.tabs \.tabs-workshop \.tab\{flex:1 1 calc\(25% - 5px\) !important\}", code)
        self.assertIsNotNone(m, "between the phone strip and one full row, the eight tabs wrap 7+1 again (VAULT alone)")
        self.assertGreaterEqual(int(m.group(1)), 820, "the four-to-a-row band must reach the width that first holds all eight")

    def test_the_code_names_no_vault_store_no_mule_function_and_no_dialog(self):
        js = _chars_js(_src())
        code = re.sub(r"/\*.{0,6000}?\*/", " ", js, flags=re.S)
        code = "\n".join(re.sub(r"(^|[^:'\"])//.*$", r"\1", l) for l in code.split("\n"))
        self.assertGreater(len(code), 2000, "the comment strip ate the code - measure the real thing")
        self.assertEqual(sorted(set(re.findall(r"d2r_\w+", code))), ["d2r_cbMain", "d2r_charBuilds"],
                         "the Characters block names a store that is not its own")
        for bad in ("d2r_mule", "d2r_owned", "d2r_foundLog", "d2r_vault", "vaultAssign", "vaultAutoAssign",
                    "openMuleCard", "_muleLoad", "tvVaultRegister", "renderVault", "muleById",
                    "alert(", "confirm(", "prompt("):
            self.assertNotIn(bad, code, "the Characters block's code names %s" % bad)


RED_PROOF = [
    {
        "why": "his answer 2026-09-26 - the console header loses its Characters door",
        "file": "control_ui.html",
        "find": "data-tab=\"chars\" title=\"Characters - your own builds\"",
        "replace": "data-tab=\"charsX\" title=\"Characters - your own builds\"",
        "matches": 1,
    },
    {
        "why": "#245 - the Characters tab leaves the top bar: the room exists and has no door",
        "file": "bible.html",
        "find": '    <button class="tab" data-tab="chars">👤 Characters</button>',
        "replace": "    ",
        "matches": 1,
    },
    {
        "why": "#245 - the console shell never re-shows the Characters tab (app context hides every tab it does not name)",
        "file": "bible.html",
        "find": 'body.app-ctx .tabs .tab[data-tab="chars"],\n',
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 - entering the tab does not repaint it, so a build saved in the planner is missing until reload",
        "file": "bible.html",
        "find": "  if (name === \"chars\"){ try { if (typeof window.renderCharsTab === 'function') window.renderCharsTab(); } catch(e){} }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 - the MAIN character stops leading the list",
        "file": "bible.html",
        "find": "      if (a === mainId) return -1;\n      if (c === mainId) return 1;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 - Set as MAIN also writes a mule store: the manual side reaches into the vault",
        "file": "bible.html",
        "find": "    window.LSR.setItem(K_MAIN, String(id));\n",
        "replace": "    window.LSR.setItem(K_MAIN, String(id)); window.LSR.setItem('d2r_muleAssign', '{}');\n",
        "matches": 1,
    },
    {
        "why": "#245 - Delete is one click: the first press removes the build with no confirm",
        "file": "bible.html",
        "find": "    if (!own.call(armed, id)){\n      armed[id] = setTimeout(",
        "replace": "    if (false){\n      armed[id] = setTimeout(",
        "matches": 1,
    },
    {
        "why": "#245 - the confirm never lapses: a press minutes later still deletes",
        "file": "bible.html",
        "find": "      armed[id] = setTimeout(function(){ delete armed[id]; _render(); }, ARM_MS);\n",
        "replace": "      armed[id] = 1;\n",
        "matches": 1,
    },
    {
        "why": "#245 - Undo re-serialises the store instead of restoring it byte-identical",
        "file": "bible.html",
        "find": "        window.LSR.setItem(K_BUILDS, cur);\n",
        "replace": "        window.LSR.setItem(K_BUILDS, JSON.stringify(JSON.parse(cur)));\n",
        "matches": 1,
    },
    {
        "why": "#245 review - Undo is byte-identical only last-first: undone in the bar's order, the store comes back a different string",
        "file": "bible.html",
        "find": "      if (chain && r.raw === prev){\n",
        "replace": "      if (!later.length && r.raw === prev){\n",
        "matches": 1,
    },
    {
        "why": "#245 review - the countdown rebuilds the Undo bar every second, so the Undo button he is on is replaced and his Enter / slow click is lost",
        "file": "bible.html",
        "find": "    if (sig === undoSig){\n",
        "replace": "    if (false){\n",
        "matches": 1,
    },
    {
        "why": "#245 review - a repaint drops keyboard focus to <body>: Enter arms Delete and the second Enter does nothing",
        "file": "bible.html",
        "find": "    if (back) _refocus(back);\n",
        "replace": "    if (false) _refocus(back);\n",
        "matches": 1,
    },
    {
        "why": "#245 review - one double-click deletes: its second click confirms the arm its first click made",
        "file": "bible.html",
        "find": "    if (Date.now() - (armedAt[id] || 0) < CONFIRM_MIN_MS) return 'armed';",
        "replace": "    if (false) return 'armed';",
        "matches": 1,
    },
    {
        "why": "#245 review - the room deletes the build the open planner is showing, and every edit after it is dropped",
        "file": "bible.html",
        "find": "    if (document.documentElement.classList.contains('cb-lock')){ _say(SAY_BUILDER); return 'builder-open'; }\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 review - another window deletes the build on screen and the planner keeps showing it (no storage listener)",
        "file": "bible.html",
        "find": "      if (!Object.prototype.hasOwnProperty.call(_cbAll(), st.bid)) _cbGone();\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 review - an edit to a build that is no longer saved is dropped in silence (_cbCommit returns false and says nothing)",
        "file": "bible.html",
        "find": "    if (!b){ if (st.bid) _cbGone(); return false; }\n",
        "replace": "    if (!b) return false;\n",
        "matches": 1,
    },
    {
        "why": "#245 review - the planner's render returns before painting when its build is gone, leaving the stale build on screen",
        "file": "bible.html",
        "find": "    if (!b){ if (st.bid && !st.draft && !st.newb) _cbGone(); return; }",
        "replace": "    if (!b) return;",
        "matches": 1,
    },
    {
        "why": "#245 review - app context's row is centred again and overflows past its left edge, where no scroll reaches",
        "file": "bible.html",
        "find": "body.app-ctx .tabs{justify-content:flex-start !important}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 review - between 701 px and one full row, app context's eight tabs wrap 7+1 again (VAULT alone on a row)",
        "file": "bible.html",
        "find": "  body.app-ctx:not(.engine-driven) .tabs .tabs-workshop .tab{flex:1 1 calc(25% - 5px) !important}\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 - the Undo never expires: a deleted build can be resurrected long after the 20 s",
        "file": "bible.html",
        "find": "    u.timer = setTimeout(function(){ _drop(u); _render(); }, UNDO_MS);\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 - deleting the MAIN leaves d2r_cbMain pointing at a build that is gone",
        "file": "bible.html",
        "find": "    if (wasMain) window.LSR.removeItem(K_MAIN);\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#245 - Open ignores the card and opens whichever build the planner last had",
        "file": "bible.html",
        "find": "    return window.openCharBuilder(id);\n",
        "replace": "    return window.openCharBuilder();\n",
        "matches": 1,
    },
    {
        "why": "#245 - closing the planner does not repaint the room, so an edit made there is invisible here",
        "file": "bible.html",
        "find": "      if (wasOpen && !open) _render();",
        "replace": "      if (false) _render();",
        "matches": 1,
    },
    {
        "why": "#245 - an unparseable store reads as 'no characters' and a delete writes {} over his builds",
        "file": "bible.html",
        "find": "    catch (e) { return { ok: false, why: 'the saved builds are not readable (' + (e && e.message || e) + ')' }; }\n",
        "replace": "    catch (e) { return { ok: true, all: {}, raw: raw }; }\n",
        "matches": 1,
    },
    {
        "why": "#245 - the builder's build dropdown stops marking the MAIN",
        "file": "bible.html",
        "find": "(id === mainId ? '★ MAIN · ' : '')",
        "replace": "''",
        "matches": 1,
    },
    {
        "why": "#245 - the MAIN pointer stops forking per account: a ladder MAIN overwrites the main account's",
        "file": "bible.html",
        "find": '  "d2r_cbMain",\n',
        "replace": "",
        "matches": 1,
    },
]


if __name__ == "__main__":
    if NODE is None:
        sys.stderr.write("⚪ SKIP — node is not on this machine, so the Characters tab was not driven. UNMEASURED, declared (77).\n")
        raise SystemExit(77)
    unittest.main(verbosity=2)
