# -*- coding: utf-8 -*-
"""#194 (REG-3096) - IN A SNAPSHOT SHADOW NO DRAG AND NO CONTROL ON THE VAULT, D2JSP, TV·D OR RUNES TAB WRITES ANYTHING.

GrokBot proved on the guest at v3806 that 0 stores change across 40 controls x 11 tabs in a shadow, and left two parts
UNKNOWN: DRAG (vault tiles, dock to mule, mule to mule), and the Vault, d2jsp, TV·D and Runes tabs, which had no store
counter to compare. This is the code half of that two-way: the WHOLE page (vault_page_node) boots twice in node.

  OWN: his board, with a vault filed by the page's own doors (hand adds, vaultAssign to two lockers, one tile placed by
       hand with _mpPlace). The same drags
       and the same sweep run here first, and they MUST write - the baseline that proves the harness can see a write.
  SHADOW: a viewer's board in a snapshot shadow of exactly those stores (?tvd-shadow=1, the snapshot on the parent, as the
       console's frame hands it). The shadow boot and its veil are the page's own; nothing is stubbed.

What runs in each: five drags by the page's own handlers - the right click that unlocks a tile he placed, the keyboard
carry (Enter, an arrow, Enter), the tile pointer-dragged to an empty cell, the same onto a Mule tab (mule to mule), and a
dock chip (the dock's own markup) dragged onto a locker's plate - then
every control the four tabs paint (each element with a handler, each button, link, field, tile, cell and plate) gets a
press, a click, Enter / Arrow / Space / Delete / letter keys, input and change, a right click, and a drag start, drag
over, drop and drag end. Events run in a browser's order through the page's own listeners: window and document capture,
the target's and its ancestors' inline handlers, then document and window bubble, with each stop honoured.

Watched: the viewer's real storage (every setItem / removeItem / clear), the shadow's memory store (every write the page
attempts, which the frame swallows), the network the page reaches (fetch, XHR, beacon, window.open) and every fetch it
attempts through the veil. In the shadow: no real write at all, no attempted write from any drag or control, no request
that is not a GET, nothing under /api/ reaching the network. The one attempt a tab open makes - switchTab's
d2r_activeTab, which tab is on screen - lands in the frame's memory and is named below.

The harness reads storage as a browser does: vault_page_node binds its store as a top-level const, which the page's bare
`localStorage` would resolve to past the shadow's window.localStorage; this law rebinds that one name (two anchors, each
asserted) so the page's bare and window-qualified names are the one property, as in a browser. RED_PROOF below.
"""
import io
import json
import os
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
import vault_page_node as VPN  # noqa: E402

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
TAB_IDS = ("tab-d2jsp", "tab-runes", "tab-tvd", "tab-vault")   # the vault last: its sweep removes what it files, on his board
#: the one write a shadow attempts on a tab open: switchTab's d2r_activeTab (which tab is on screen), straight into the
#: frame's memory store, whose setItem the shadow boot made a no-op - it lands nowhere
TAB_OPEN_OK = ["setItem:d2r_activeTab"]
#: view state a control the veil lets through asks the storage door to keep - never a d2r_* key, and the door drops it in a
#: shadow (LSR.setItem returns at window._tvdShadow). A d2r_* attempt from any control or drag is a defect, always.
UI_OK = {"vaultTasksOpen": "the MOVE TASKS panel open or shut (vaultTasksTog, a VIEW handler)"}
#: vault_page_node's store is a top-level const; a browser's bare `localStorage` is the window's property
#: each drag the law drives, and the store it writes on his board (the baseline): the right click's unlock of a tile he
#: placed, the keyboard carry (Enter, an arrow, Enter), a tile pointer-dragged to an empty cell, the same onto a Mule tab,
#: and a dock chip dropped on a locker's plate
DRAGS = {"unlock": "d2r_mulePos", "keyCarry": "d2r_mulePos", "toCell": "d2r_mulePos", "toMuleTab": "d2r_mulePos",
         "chipToMule": "d2r_muleAssign"}
REBIND = (("const localStorage = {", "const __vpnLocalStorage = {"),
          ("{ value: localStorage, configurable: true", "{ value: __vpnLocalStorage, configurable: true"))

FDOM = r"""
/* FDOM - the painted tab as a tree, events through the page's own listeners in browser order */
var FD = (function () {
  var VOID = { area: 1, base: 1, br: 1, col: 1, embed: 1, hr: 1, img: 1, input: 1, link: 1, meta: 1, source: 1, track: 1, wbr: 1 };
  var UNSUP = {};
  function N(tag, attrs, parent) {
    this.tag = tag; this.attrs = attrs; this.parent = parent; this.parentNode = parent; this.parentElement = parent;
    this.kids = []; this.children = this.kids; this.cls = String(attrs['class'] || '').split(/\s+/).filter(Boolean);
    this.value = attrs.value != null ? attrs.value : ''; this.checked = 'checked' in attrs; this.disabled = 'disabled' in attrs;
    this.style = {}; this._ds = null; this.hidden = 'hidden' in attrs; this.open = 'open' in attrs;
  }
  function camel(s) { return s.replace(/-([a-z])/g, function (m, c) { return c.toUpperCase(); }); }
  N.prototype = {
    nodeType: 1,
    getAttribute: function (k) { return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; },
    hasAttribute: function (k) { return Object.prototype.hasOwnProperty.call(this.attrs, k); },
    setAttribute: function (k, v) { this.attrs[k] = String(v); this._ds = null; },
    removeAttribute: function (k) { delete this.attrs[k]; this._ds = null; },
    get id() { return this.attrs.id || ''; },
    get tagName() { return this.tag.toUpperCase(); },
    get nodeName() { return this.tag.toUpperCase(); },
    get className() { return this.cls.join(' '); },
    get dataset() {
      if (!this._ds) { var d = {}; for (var k in this.attrs) if (k.indexOf('data-') === 0) d[camel(k.slice(5))] = this.attrs[k]; this._ds = d; }
      return this._ds;
    },
    get classList() {
      var s = this;
      return { contains: function (c) { return s.cls.indexOf(c) >= 0; }, add: function () { for (var i = 0; i < arguments.length; i++) if (s.cls.indexOf(arguments[i]) < 0) s.cls.push(arguments[i]); },
               remove: function () { var a = [].slice.call(arguments); s.cls = s.cls.filter(function (x) { return a.indexOf(x) < 0; }); },
               toggle: function (c, on) { if (on === undefined) on = s.cls.indexOf(c) < 0; if (on) this.add(c); else this.remove(c); return on; } };
    },
    matches: function (sel) { var me = this; return splitList(sel).some(function (s) { return matchComplex(me, s); }); },
    closest: function (sel) { for (var n = this; n; n = n.parent) if (n.matches(sel)) return n; return null; },
    contains: function (x) { for (var n = x; n; n = n.parent) if (n === this) return true; return false; },
    querySelectorAll: function (sel) { var out = []; walk(this, function (n) { if (n.matches(sel)) out.push(n); }); return out; },
    querySelector: function (sel) { return this.querySelectorAll(sel)[0] || null; },
    getBoundingClientRect: function () { return { left: 0, top: 0, width: 10, height: 10, right: 10, bottom: 10, x: 0, y: 0 }; },
    get textContent() { var t = ''; walk(this, function (n) { if (n.text) t += n.text; }); return t; },
    get innerText() { return this.textContent; },
    get innerHTML() { return ''; }, set innerHTML(v) {},
    focus: function () {}, blur: function () {}, click: function () {}, select: function () {}, scrollIntoView: function () {},
    appendChild: function (c) { return c; }, removeChild: function (c) { return c; }, remove: function () {},
    insertBefore: function (c) { return c; }, insertAdjacentHTML: function () {}, insertAdjacentElement: function (p, c) { return c; },
    get nextElementSibling() { var s = this.parent ? this.parent.kids.filter(function (k) { return k.tag; }) : []; return s[s.indexOf(this) + 1] || null; },
    get previousElementSibling() { var s = this.parent ? this.parent.kids.filter(function (k) { return k.tag; }) : []; return s[s.indexOf(this) - 1] || null; },
    addEventListener: function () {}, removeEventListener: function () {}, dispatchEvent: function () { return true; },
    setPointerCapture: function () {}, releasePointerCapture: function () {},
    clientLeft: 0, clientTop: 0
  };
  function walk(n, f) { for (var i = 0; i < n.kids.length; i++) { var k = n.kids[i]; if (k.tag) { f(k); walk(k, f); } } }
  function splitList(sel) {
    var out = [], d = 0, q = null, cur = '';
    for (var i = 0; i < sel.length; i++) {
      var c = sel[i];
      if (q) { cur += c; if (c === q) q = null; continue; }
      if (c === '"' || c === "'") { q = c; cur += c; continue; }
      if (c === '[' || c === '(') d++; if (c === ']' || c === ')') d--;
      if (c === ',' && !d) { out.push(cur.trim()); cur = ''; continue; }
      cur += c;
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }
  function parts(s) {   // descendant / child combinators, both read as "inside"
    var out = [], d = 0, q = null, cur = '';
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (q) { cur += c; if (c === q) q = null; continue; }
      if (c === '"' || c === "'") { q = c; cur += c; continue; }
      if (c === '[' || c === '(') d++; if (c === ']' || c === ')') d--;
      if ((c === ' ' || c === '>') && !d) { if (cur.trim()) out.push(cur.trim()); cur = ''; continue; }
      cur += c;
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }
  function matchCompound(n, s) {
    var re = /^(\*|[a-zA-Z][\w-]*)?|#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:([\^*$]?=)["']?([^"'\]]*)["']?)?\]|:not\(([^)]*)\)|:([\w-]+)/g, m, any = false, pos = 0;
    var first = /^(\*|[a-zA-Z][\w-]*)/.exec(s);
    if (first) { if (first[1] !== '*' && first[1].toLowerCase() !== n.tag) return false; pos = first[0].length; }
    var rest = s.slice(pos), r2 = /#([\w-]+)|\.([\w-]+)|\[([\w-]+)(?:([\^*$]?=)["']?([^"'\]]*)["']?)?\]|:not\(([^)]*)\)|:([\w-]+)/g, eaten = 0;
    while ((m = r2.exec(rest))) {
      if (m.index !== eaten) { UNSUP[s] = 1; return false; }
      eaten = r2.lastIndex;
      if (m[1] != null) { if (n.id !== m[1]) return false; }
      else if (m[2] != null) { if (n.cls.indexOf(m[2]) < 0) return false; }
      else if (m[3] != null) {
        var v = n.getAttribute(m[3]);
        if (v == null) return false;
        if (m[4] === '=' && v !== m[5]) return false;
        if (m[4] === '^=' && v.indexOf(m[5]) !== 0) return false;
        if (m[4] === '*=' && v.indexOf(m[5]) < 0) return false;
        if (m[4] === '$=' && v.slice(-m[5].length) !== m[5]) return false;
      }
      else if (m[6] != null) { if (n.matches(m[6])) return false; }
      else if (m[7] != null) { if (m[7] === 'checked') { if (!n.checked) return false; } else if (m[7] !== 'hover' && m[7] !== 'focus') { UNSUP[s] = 1; return false; } }
    }
    if (eaten !== rest.length) { UNSUP[s] = 1; return false; }
    return true;
  }
  function matchComplex(n, s) {
    var ps = parts(s);
    if (!matchCompound(n, ps[ps.length - 1])) return false;
    var a = n.parent;
    for (var i = ps.length - 2; i >= 0; i--) {
      while (a && !matchCompound(a, ps[i])) a = a.parent;
      if (!a) return false;
      a = a.parent;
    }
    return true;
  }
  function unent(s) { return String(s).replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); }
  function parse(html, root) {
    var stack = [root], re = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w-]*)((?:[^>"']|"[^"]*"|'[^']*')*)>|([^<]+)/g, m;
    while ((m = re.exec(html))) {
      var top = stack[stack.length - 1];
      if (m[4] != null) { top.kids.push({ text: unent(m[4]) }); continue; }
      if (!m[2]) continue;
      var tag = m[2].toLowerCase();
      if (m[1]) {
        for (var i = stack.length - 1; i > 0; i--) if (stack[i].tag === tag) { stack.length = i; break; }
        continue;
      }
      var attrs = {}, ar = /([^\s=\/]+)(?:\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+)))?/g, am;
      while ((am = ar.exec(m[3]))) attrs[am[1].toLowerCase()] = unent(am[3] != null ? am[3] : am[4] != null ? am[4] : am[5] != null ? am[5] : '');
      var n = new N(tag, attrs, top);
      top.kids.push(n);
      if (!VOID[tag] && !/\/\s*$/.test(m[3])) stack.push(n);
    }
  }
  /* the static markup of a tab, its painted containers swapped in (an El the page painted by innerHTML), recursively */
  function tab(page, id, ELS) {
    var at = page.indexOf('<div class="tab-content" id="' + id + '">');
    var body = page.slice(at).replace(/<script[\s\S]*?<\/script>/g, '').replace(/<style[\s\S]*?<\/style>/g, '');
    var root = new N('#root', {}, null);
    parse(body, root);
    var t = root.kids.filter(function (k) { return k.tag; })[0];
    if (t) t.parent = null;
    var seen = {};
    (function hydrate(n, depth) {
      if (depth > 12) return;
      for (var i = 0; i < n.kids.length; i++) {
        var k = n.kids[i];
        if (!k.tag) continue;
        var el = k.id && ELS.get(k.id);
        if (el && el._html && !seen[k.id]) { seen[k.id] = 1; k.kids = []; k.children = k.kids; parse(el._html, k); }
        hydrate(k, depth + 1);
      }
    })(t, 0);
    return t;
  }
  return { N: N, parse: parse, tab: tab, walk: walk, UNSUP: UNSUP };
})();

/* the page's listeners in the order a browser runs them: window capture, document capture, the target and its
   ancestors' inline handlers (bubble), document bubble, window bubble; stopPropagation / stopImmediatePropagation honoured */
function fireOn(type, target, extra) {
  var ev = { type: type, target: target, key: '', code: '', button: 0, buttons: 1, pointerId: 7, clientX: 5, clientY: 5, detail: 1,
    shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, cancelable: true, bubbles: true, isTrusted: true,
    defaultPrevented: false, _stop: false, _imm: false, errs: [],
    dataTransfer: DT, preventDefault: function () { this.defaultPrevented = true; },
    stopPropagation: function () { this._stop = true; }, stopImmediatePropagation: function () { this._stop = true; this._imm = true; } };
  for (var k in (extra || {})) ev[k] = extra[k];
  var all = REC.filter(function (r) { return r.t === type; });
  function run(list) {
    for (var i = 0; i < list.length && !ev._imm; i++) {
      try { list[i].f.call(list[i].where === 'window' ? window : document, ev); }
      catch (e) { ev.errs.push(list[i].where + ':' + String(e && e.message || e).slice(0, 120)); }
    }
  }
  run(all.filter(function (r) { return r.where === 'window' && r.cap; }));
  if (!ev._stop) run(all.filter(function (r) { return r.where === 'document' && r.cap; }));
  for (var n = target; n && n.tag && !ev._stop; n = n.parent) {
    var code = n.getAttribute('on' + type);
    if (!code) continue;
    try { (new Function('event', code)).call(n, ev); } catch (e) { ev.errs.push('inline:' + String(e && e.message || e).slice(0, 120)); }
  }
  if (!ev._stop) run(all.filter(function (r) { return r.where === 'document' && !r.cap; }));
  if (!ev._stop) run(all.filter(function (r) { return r.where === 'window' && !r.cap; }));
  return ev;
}
var DT = { _d: {}, setData: function (k, v) { this._d[k] = String(v); }, getData: function (k) { return this._d[k] || ''; },
           clearData: function () { this._d = {}; }, effectAllowed: 'all', dropEffect: 'none', files: [], items: [], types: [] };
"""

SPIES = r"""
var REC = [], NET = [], REALW = []; if (typeof LEAVES === 'undefined') var LEAVES = [];
if (!/tvd-shadow/.test(String(location.search))) {
  localStorage.setItem('d2r_ownerClaim', '*');
  localStorage.setItem('d2r_owned', JSON.stringify(['Windforce']));
}
(function () {
  var dA = document.addEventListener;
  document.addEventListener = function (t, f, o) { REC.push({ where: 'document', t: t, f: f, cap: o === true || !!(o && o.capture) }); return dA.apply(this, arguments); };
  var wA = window.addEventListener;
  window.addEventListener = function (t, f, o) { REC.push({ where: 'window', t: t, f: f, cap: o === true || !!(o && o.capture) }); return wA.apply(this, arguments); };
  var R = localStorage;   /* the viewer's real store: every write to it, from here on */
  ['setItem', 'removeItem', 'clear'].forEach(function (m) { var o = R[m]; R[m] = function (k) { REALW.push(m + ':' + k); return o.apply(this, arguments); }; });
  window.fetch = function (u, i) { NET.push(['fetch', String(u && u.url || u), String((i && i.method) || 'GET').toUpperCase()]); return new Promise(function () {}); };
  window.XMLHttpRequest = function () { this.open = function (m, u) { this._m = m; this._u = u; }; this.send = function () { NET.push(['xhr', String(this._u), String(this._m).toUpperCase()]); };
    this.setRequestHeader = function () {}; this.abort = function () {}; this.addEventListener = function () {}; };
  navigator.sendBeacon = function (u) { NET.push(['beacon', String(u), 'POST']); return true; };
  window.open = function (u) { NET.push(['open', String(u), 'GET']); return null; };
})();
"""

SHADOW_PRE = r"""
var LEAVES = [];
document.write = function (t) { OUT.shadowRefused = String(t).replace(/<[^>]*>/g, '').slice(0, 300); };
window.stop = function () {};
location.search = '?tvd-shadow=1'; location.href = 'http://127.0.0.1/bible.html?tvd-shadow=1';
window.parent = { _tvdShadowSnap: SNAP, postMessage: function (m) { LEAVES.push(m && m.type); } };
"""

SEED = r"""
var W = window;
try { W._vaultAutoIntakeSet(false); } catch (e) {}
var ADDED = [];
['Harlequin Crest', 'Stone of Jordan', 'Gull', 'Arachnid Mesh', 'Skin of the Vipermagi'].forEach(function (n) {
  try { var r = W.vaultHandAdd(n); ADDED.push(r && r.name || null); } catch (e) { ADDED.push('ERR ' + e.message); } });
[['Harlequin Crest (Shako)', 'uni-armor'], ['Arachnid Mesh', 'uni-armor'], ['Skin of the Vipermagi', 'uni-armor'], ['Gull (dagger)', 'uni-weap']].forEach(function (a) {
  try { W.vaultAssign(a[0], a[1]); } catch (e) { ADDED.push('ASSIGN ERR ' + e.message); } });
try { OUT.placed = W._mpPlace('uni-armor', 'Skin of the Vipermagi', { tab: 'personal', page: 0, x: 0, y: 0 }); } catch (e) { OUT.placed = String(e.message); }
try { W.renderVault(); } catch (e) {}
H.flush(60, 3);
OUT.added = ADDED;
OUT.snap = {}; H.RAW.forEach(function (v, k) { if (/^d2r_[A-Za-z0-9_]{1,60}$/.test(k)) OUT.snap[k] = v; });
"""

DRIVE = r"""
var W = window;
var shadow = !!W._tvdShadow;
/* a handler's rejected promise (a dialog the stand-in DOM cannot draw) is that handler's error, never the run's end */
var UNHANDLED = [];
process.on('unhandledRejection', function (e) { UNHANDLED.push(String(e && e.message || e).slice(0, 160)); });
/* a rejection lands after the body ran: it is reported on its own line when node exits */
process.on('exit', function () { process.stdout.write('\n__R3096_UNHANDLED__' + JSON.stringify(UNHANDLED) + '\n'); });
/* the tab strip: the harness answers only #id selectors, and switchTab asks for its tab button first */
(function () { var qs = document.querySelector, btns = {};
  document.querySelector = function (sel) { var m = /^\.tab\[data-tab="([\w-]+)"\]$/.exec(String(sel).trim());
    if (m) return btns[m[1]] || (btns[m[1]] = document.createElement('button')); return qs.call(document, sel); }; })();
var MEMW = [], ATT = [];
/* the board's one storage door: in a shadow it drops every write at its first line (window._tvdShadow), so an attempt
   is seen here or nowhere */
if (W.LSR) ['setItem', 'removeItem'].forEach(function (m) { var o = W.LSR[m]; W.LSR[m] = function (k) { if (shadow) MEMW.push('LSR.' + m + ':' + k); return o.apply(this, arguments); }; });
if (shadow) {
  var M = W.localStorage;
  ['setItem', 'removeItem', 'clear'].forEach(function (m) { var o = M[m]; M[m] = function (k) { MEMW.push(m + ':' + k); return o.apply(this, arguments); }; });
  var VF = W.fetch;   /* the veil's own fetch: every request the page attempts, answered, refused or passed */
  W.fetch = function (u, i) { ATT.push([String(u && u.url || u), String((i && i.method) || 'GET').toUpperCase()]); return VF.apply(this, arguments); };
}
function marks() { return { real: REALW.length, mem: MEMW.length, net: NET.length, att: ATT.length }; }
function since(a) { return { real: REALW.slice(a.real), mem: MEMW.slice(a.mem), net: NET.slice(a.net), att: ATT.slice(a.att) }; }
var res = { shadow: shadow, boot: { real: REALW.slice(), errors: OUT.__boot ? OUT.__boot.errors : null }, tabs: {} };
var MULE = 'uni-armor', TILE = 'Skin of the Vipermagi';
function sig(n) {
  return n.tag + (n.id ? '#' + n.id : '') + (n.cls.length ? '.' + n.cls.slice(0, 2).join('.') : '') +
    (n.getAttribute('onclick') ? ' [' + n.getAttribute('onclick').slice(0, 60) + ']' : '') +
    (n.getAttribute('data-key') ? ' {' + n.getAttribute('data-key') + '}' : '');
}

/* ---- the drags, by the page's own handlers: each on a freshly painted mule window ---- */
function drags() {
  var out = {};
  function paint() {
    try { W.switchTab('vault'); W.openMuleCard(MULE); } catch (e) { out.openErr = String(e.message); }
    H.flush(1000, 3);
    var root = FD.tab(TABS['tab-vault'], 'tab-vault', H.ELS), det = root.querySelector('#vault-detail');
    var tile = det && det.querySelector('.vd-item[data-key="' + TILE + '"]');
    return { root: root, det: det, tile: tile, grid: tile && tile.closest('.vd-grid[data-area]') };
  }
  function run(steps) {
    var a = marks(), errs = [], st = [];
    steps.forEach(function (p) { var ev = fireOn(p[0], p[1], p[2]); errs = errs.concat(ev.errs); st.push(p[0] + (p[2] && p[2].key ? '/' + p[2].key : '') + (ev._stop ? ':stopped' : '')); });
    H.flush(1000, 3);
    return { d: since(a), errs: errs.slice(0, 4), st: st };
  }
  function pdrag(v, target) {
    var gid = document.getElementById, efp = document.elementFromPoint;
    document.getElementById = function (id) { return id === 'vault-detail' ? v.det : gid.call(document, id); };
    document.elementFromPoint = function () { return target; };
    try { return run([['pointerdown', v.tile, { clientX: 5, clientY: 5 }], ['pointermove', v.tile, { clientX: 70, clientY: 70 }],
                      ['pointerup', v.tile, { clientX: 70, clientY: 70 }]]); }
    finally { document.getElementById = gid; document.elementFromPoint = efp; }
  }
  var v = paint();
  out.subjects = { tile: v.tile ? v.tile.getAttribute('data-key') : null, held: !!(v.tile && v.tile.classList.contains('vd-held')),
                   grid: v.grid ? v.grid.getAttribute('data-area') : null,
                   muleTabs: v.det ? v.det.querySelectorAll('.mp-settab[data-page]').length : 0,
                   plates: v.root.querySelectorAll('.vault-mule[data-vault-mule]').length };
  if (!v.tile || !v.grid) return out;
  /* the right click on a tile he placed: its unlock */
  out.unlock = run([['contextmenu', v.tile]]);
  /* the keyboard: Enter picks it up, an arrow moves its footprint, Enter drops it */
  v = paint();
  if (v.tile) out.keyCarry = run([['keydown', v.tile, { key: 'Enter' }], ['keydown', v.tile, { key: 'ArrowDown' }], ['keydown', v.tile, { key: 'Enter' }]]);
  /* the pointer: the tile onto an empty cell, then onto a Mule tab (mule to mule) */
  v = paint();
  if (v.tile && v.grid) { var cells = v.grid.querySelectorAll('.vd-cell'); out.toCell = pdrag(v, cells[cells.length - 1] || v.grid); }
  v = paint();
  if (v.tile && v.det.querySelector('.mp-settab[data-page]')) out.toMuleTab = pdrag(v, v.det.querySelector('.mp-settab[data-page]'));
  /* the dock's chip, in the markup the dock paints (renderVaultDraw), dropped on a locker's plate */
  v = paint();
  var chip = new FD.N('span', { 'class': 'vault-chip', draggable: 'true', 'data-vault-item': 'Windforce' }, v.root.querySelector('#vault-dock') || v.root);
  var plate = v.root.querySelector('.vault-mule[data-vault-mule="uni-weap"] .vm-plate') || v.root.querySelector('.vault-mule[data-vault-mule="uni-weap"]');
  if (plate) { DT.clearData(); out.chipToMule = run([['dragstart', chip], ['dragover', plate], ['drop', plate], ['dragend', chip]]); }
  return out;
}
res.drags = drags();

/* ---- every control the four tabs paint ---- */
var TABNAME = { 'tab-vault': 'vault', 'tab-d2jsp': 'd2jsp', 'tab-tvd': 'tvd', 'tab-runes': 'runes' };
var CTL = 'button, a, input, textarea, select, label, summary, [role=button], [tabindex], [draggable=true], .vault-chip, .vault-mule, .vm-plate, .vd-item, .vd-cell, .tab';
ORDER.forEach(function (tid) {
  var m0 = marks();
  try { W.switchTab(TABNAME[tid]); } catch (e) {}
  H.flush(1000, 3);
  if (tid === 'tab-vault') { try { W.openMuleCard(MULE); } catch (e) {} H.flush(1000, 3); }
  var open = since(m0);
  var root = FD.tab(TABS[tid], tid, H.ELS);
  var ctl = [];
  FD.walk(root, function (n) {
    if (Object.keys(n.attrs).some(function (k) { return /^on[a-z]+$/.test(k); }) || n.matches(CTL)) ctl.push(n);
  });
  var writers = [], erred = [], viewState = [];
  ctl.forEach(function (n) {
    var a = marks(), errs = [];
    function go(t, x) { errs = errs.concat(fireOn(t, n, x).errs); }
    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click', 'contextmenu'].forEach(function (t) { go(t); });
    ['Enter', 'ArrowRight', 'Enter', ' ', 'Delete', 'u', 'x'].forEach(function (k) { go('keydown', { key: k }); go('keyup', { key: k }); });
    if (/^(input|select|textarea)$/.test(n.tag)) { go('input'); go('change'); }
    ['dragstart', 'dragover', 'drop', 'dragend'].forEach(function (t) { go(t); });
    H.flush(1000, 3);
    var d = since(a);
    var tried = d.mem.filter(function (w) { var k = w.replace(/^[\w.]+:/, ''); return /(^|\u00b7)d2r_/.test(k) || !UI_OK[k]; });
    if (d.real.length || tried.length || d.net.length || d.att.some(function (x) { return x[1] !== 'GET'; })) writers.push({ sig: sig(n), d: d });
    else if (d.mem.length) viewState.push({ sig: sig(n), mem: d.mem });
    if (errs.length) erred.push({ sig: sig(n), errs: errs.slice(0, 3) });
  });
  res.tabs[tid] = { open: open, controls: ctl.length, writers: writers, erred: erred, viewState: viewState };
});
res.real = REALW.slice(); res.net = NET.slice(); res.att = ATT.slice();
OUT.res = res;
OUT.unsupported = Object.keys(FD.UNSUP);
"""


def _program(body, prelude):
    prog = VPN.program(body, prelude=prelude)
    for a, b in REBIND:
        if prog.count(a) != 1:
            raise AssertionError("vault_page_node moved: %r occurs %d times - this law cannot rebind its store" % (a, prog.count(a)))
        prog = prog.replace(a, b)
    return prog


def _run(body, prelude):
    if not VPN.NODE:
        raise AssertionError("node is not on this machine - this law does not skip")
    r = subprocess.run([VPN.NODE, "-"], input=_program(body, prelude), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    if r.returncode != 0:
        raise AssertionError("the page did not run in node (exit %s): %s" % (r.returncode, (r.stderr or r.stdout)[-2500:]))
    mark = "__VAULT_PAGE_NODE_OUT__"
    lines = [ln[len(mark):] for ln in (r.stdout or "").splitlines() if ln.startswith(mark)]
    if len(lines) != 1:
        raise AssertionError("the page printed %d result lines, not 1: %s" % (len(lines), (r.stderr or "")[-1200:]))
    out = json.loads(lines[0])
    late = [ln[len("__R3096_UNHANDLED__"):] for ln in (r.stdout or "").splitlines() if ln.startswith("__R3096_UNHANDLED__")]
    out["unhandled"] = json.loads(late[0]) if late else None
    return out


def _tabs():
    with io.open(BIBLE, encoding="utf-8") as fh:
        page = fh.read()
    out = {}
    for t in TAB_IDS:
        a = page.index('<div class="tab-content" id="%s">' % t)
        b = page.find('<div class="tab-content" id="tab-', a + 10)
        out[t] = page[a:(b if b > 0 else a + 400000)]
    return out


class InAShadowNoDragAndNoControlWrites(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        head = FDOM + "\nvar TABS = %s;\nvar ORDER = %s;\nvar UI_OK = %s;\n" % (json.dumps(_tabs()), json.dumps(list(TAB_IDS)),
                                                                        json.dumps(dict((k, 1) for k in UI_OK)))
        cls.own = _run(head + SEED + DRIVE, SPIES)
        snap = dict(cls.own.get("snap") or {})
        snap["d2r_api_world"] = json.dumps({"machine": "mac", "profile": "main", "os": "MAC", "ledger": "KonyoEndgame", "cousin": False})
        cls.snap_keys = sorted(snap)
        pre = "var SNAP = %s;\n" % json.dumps({"owner": "Konyo · Mac", "t": 1, "stores": snap}) + SHADOW_PRE + SPIES
        cls.sh = _run(head + DRIVE, pre)
        cls.o, cls.s = cls.own["res"], cls.sh["res"]

    # --- premises: both boards booted, the shadow is a shadow, and every subject was there to drive
    def test_premise_both_boards_boot_and_only_the_second_is_a_shadow(self):
        self.assertEqual(self.own["__boot"]["errors"], [], "his board did not boot whole in node")
        self.assertEqual(self.sh["__boot"]["errors"], [], "the shadow did not boot whole: %r" % self.sh.get("shadowRefused"))
        self.assertIs(self.o["shadow"], False)
        self.assertIs(self.s["shadow"], True, "the snapshot shadow did not open: %r" % self.sh.get("shadowRefused"))
        self.assertIn("d2r_muleAssign", self.snap_keys, "premise: the snapshot carries no filed vault")
        self.assertEqual(self.sh.get("unsupported"), [], "a selector the page asked is one this harness cannot answer")

    def test_premise_every_drag_subject_and_every_tab_was_there(self):
        for side in (self.o, self.s):
            sub = side["drags"]["subjects"]
            self.assertTrue(sub["tile"] and sub["grid"], "premise: no filed tile in the mule window: %r" % sub)
            self.assertTrue(sub["held"], "premise: the tile he placed by hand is not drawn as placed: %r" % sub)
            self.assertGreaterEqual(sub["muleTabs"], 1, "premise: the mule window has no Mule tab: %r" % sub)
            self.assertGreaterEqual(sub["plates"], 10, "premise: the lockers' plates are missing: %r" % sub)
            for k in DRAGS:
                self.assertIn(k, side["drags"], "premise: the %s drag never ran" % k)
        for tid, least in (("tab-vault", 200), ("tab-d2jsp", 10), ("tab-runes", 20), ("tab-tvd", 10)):
            self.assertGreaterEqual(self.s["tabs"][tid]["controls"], least, "premise: the shadow's %s painted %d controls" %
                                    (tid, self.s["tabs"][tid]["controls"]))

    def test_premise_every_handler_the_shadow_let_through_ran_to_its_end(self):
        bad = dict((t, v["erred"]) for t, v in self.s["tabs"].items() if v["erred"])
        self.assertEqual(bad, {}, "a handler threw in node, so whether it writes is UNKNOWN")
        self.assertEqual(self.sh["unhandled"], [], "a shadow handler's promise failed, so whether it writes is UNKNOWN")

    # --- the baseline: on his board the same drags and sweep write, so a write is visible to this harness
    def test_on_his_board_every_drag_writes(self):
        d = self.o["drags"]
        for k, key in DRAGS.items():
            self.assertIn("setItem:" + key, d[k]["d"]["real"], "baseline: the %s drag wrote no %s on his board: %r" % (k, key, d[k]))

    def test_on_his_board_the_sweep_writes(self):
        for tid in ("tab-vault", "tab-runes"):
            self.assertGreater(len(self.o["tabs"][tid]["writers"]), 5, "baseline: %s's controls wrote nothing on his board" % tid)

    # --- the shadow
    def test_in_a_shadow_no_drag_starts_and_none_writes(self):
        d = self.s["drags"]
        self.assertEqual(d["toCell"]["st"][0], "pointerdown:stopped", "the tile's press reached the mule window: %r" % d["toCell"])
        self.assertEqual(d["toMuleTab"]["st"][0], "pointerdown:stopped")
        self.assertEqual(d["unlock"]["st"], ["contextmenu:stopped"], "the right click reached the placed tile: %r" % d["unlock"])
        self.assertEqual([x for x in d["chipToMule"]["st"] if x.endswith(":stopped")], ["dragstart:stopped", "drop:stopped"],
                         "the chip's drag or its drop reached the vault: %r" % d["chipToMule"])
        for k in DRAGS:
            self.assertEqual(d[k]["d"], {"real": [], "mem": [], "net": [], "att": []}, "the %s drag wrote, or tried to, in a shadow" % k)

    def test_in_a_shadow_no_control_on_the_four_tabs_writes(self):
        live = dict((t, v["writers"]) for t, v in self.s["tabs"].items() if v["writers"])
        self.assertEqual(live, {}, "a control wrote, or tried to, in a shadow")

    def test_in_a_shadow_the_viewers_real_storage_is_never_written(self):
        self.assertEqual(self.s["boot"]["real"], [], "the shadow wrote the viewer's real storage at boot")
        self.assertEqual(self.s["real"], [], "the shadow wrote the viewer's real storage")

    def test_in_a_shadow_nothing_but_a_read_is_attempted_and_nothing_under_api_leaves(self):
        self.assertEqual([a for a in self.s["att"] if a[1] != "GET"], [], "a shadow attempted a request that is not a read")
        self.assertEqual([n for n in self.s["net"] if n[2] != "GET" or "/api" in n[1]], [],
                         "a shadow request reached the network: %r" % self.s["net"])

    def test_view_state_a_shadow_asks_to_keep_is_named_and_never_a_d2r_store(self):
        keys = set(w.replace("LSR.setItem:", "").replace("LSR.removeItem:", "")
                   for v in self.s["tabs"].values() for r in v["viewState"] for w in r["mem"])
        self.assertTrue(keys <= set(UI_OK), "view state nobody named: %r" % (keys - set(UI_OK)))
        self.assertFalse(any("d2r_" in k for k in UI_OK), "a d2r_* store is never view state")

    def test_a_tab_open_attempts_only_the_tab_it_shows(self):
        for tid, v in self.s["tabs"].items():
            self.assertEqual(v["open"]["real"], [], "opening %s wrote the viewer's real storage" % tid)
            self.assertEqual(v["open"]["mem"], TAB_OPEN_OK, "opening %s attempted %r" % (tid, v["open"]["mem"]))


RED_PROOF = [
    {"why": "REG-3096 - a tile's press reaches the mule window in a shadow (the drag moves and writes)",
     "file": "bible.html",
     "find": "!t.closest('.vd-item[data-key], .vd-item[data-dbkey], [onpointerdown], [onmousedown]')) return;",
     "replace": "!t.closest('[onpointerdown], [onmousedown]')) return;",
     "matches": 1},
    {"why": "REG-3096 - a dock chip's drag and its drop reach the vault in a shadow",
     "file": "bible.html",
     "find": "    ['change', 'input', 'submit', 'drop', 'paste', 'dragstart', 'contextmenu'].forEach(",
     "replace": "    ['change', 'input', 'submit', 'paste', 'contextmenu'].forEach(",
     "matches": 1},
    {"why": "REG-3096 - every click passes the shadow's veil (the tabs' write buttons write)",
     "file": "bible.html",
     "find": "    function viewOnly(el) {\n",
     "replace": "    function viewOnly(el) {\n      return true;\n",
     "matches": 1},
    {"why": "REG-3096 - every key reaches the four tabs' own handlers in a shadow",
     "file": "bible.html",
     "find": "    window._tvdShadowKeyOk = function (ev) {\n",
     "replace": "    window._tvdShadowKeyOk = function (ev) {\n      return true;\n",
     "matches": 1},
    {"why": "REG-3096 - a right click reaches a mule tile in a shadow (its context unlock)",
     "file": "bible.html",
     "find": "    ['change', 'input', 'submit', 'drop', 'paste', 'dragstart', 'contextmenu'].forEach(",
     "replace": "    ['change', 'input', 'submit', 'drop', 'paste', 'dragstart'].forEach(",
     "matches": 1},
    {"why": "REG-3096 - a shadow's /api/ reads go out to the network instead of being refused",
     "file": "bible.html",
     "find": "      if (blocked(url, method)) { window._tvdShadowRefused++; return refused(foreign(url) ? 403 : 200); }\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
