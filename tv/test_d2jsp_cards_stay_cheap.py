# -*- coding: utf-8 -*-
"""v3773 (spec D1) - a long D2JSP list does not freeze the console window.

The console window is WebKitGTK. It paints CSS filter / drop-shadow in software.
On a 228-card D2JSP list v3771 held the main thread 93-98% of the time and grew
the web process past 3 GB (the guard killed it at 3.5 GB); Chrome never showed
it. Four laws, each read where it can be read:

  1. CSS (static): in the D2JSP room the card art has no filter and the card is
     its own content-visibility:auto box with an intrinsic size. The glow is a
     baked radial gradient instead.
  2. A reading, a sold toggle or a typed fg repaints its own card only (node).
  3. Options keeps the list: opening the picker repaints no card, and the D2JSP
     desk builds its 1,220-row builder list once per query (node).
  4. Screens: Chrome counts every element computing any filter (not only
     drop-shadow or blur) inside a D2JSP card and outside a contained card in
     D2JSP, Vault and Runewords, and the cards a reading or an Options click
     touches. WebKitGTK opens D2JSP with 228 synthetic filings, refreshes the
     prices and opens Options twice under a 3 GB kill guard; it judges the
     blocked share of the main thread and the web process's memory growth.

RED_PROOF below; every entry changes behaviour. The screen halves run only
outside a heart2 sandbox. No Chrome or no WebKitGTK is a declared skip.
[[heart-first]] [[unknown-stays-unknown]] [[regression-guard]]
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

from test_input_stays_responsive import (  # noqa: E402
    NODE, _node, code_mask, css_rules, _decl, _free_port, _chrome_proc, _new_tab, _connect, _ev_async)

BIBLE = os.path.join(ROOT, "bible.html")
NO_BROWSER = "no Chrome/Chromium on this machine"
NO_WEBKIT = "no WebKitGTK (gi WebKit2 + xvfb-run) on this machine"
SKIPS = set()

CARDS = 228                    # his live list when it froze
FILTER_BUDGET = {"d2jsp": 0, "vault": 24, "forge": 32}   # elements computing any filter outside a contained card
                               # (forge: 29 colour filters on v3771 and v3773 alike; a follow-up in REG-2294)
CARD_FILTERS = 0               # elements computing any filter inside a D2JSP card
ROOMS = ("d2jsp", "vault", "forge")   # D2JSP, Vault, Runewords
REPORT_ROOMS = ("funi", "fsets", "crafts")
READING_CARDS = 1              # cards one reading may touch
OPTIONS_CARDS = 8              # cards an Options open may touch (late readings land on their own card)
WK_BLOCKED_PCT = 40            # main-thread share blocked, per phase window after idle
                               # (v3771 d2jsp open 96% then killed at 3.3 GB; the fix 6-13%)
WK_RSS_GROWTH_MB = 1024        # web process growth over its idle size
WK_KILL_KB = 3 * 1024 * 1024   # the 3 GB guard: never run WebKit without it


def _read():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _block(src, pattern):
    """The source of the brace block opened by the first match of `pattern`, read with
    comments, strings and regexes masked so a brace inside one does not count."""
    m = re.search(pattern, src)
    if not m:
        return None
    window = src[m.start():m.start() + 60000]
    masked = code_mask(window)
    i = masked.index("{", m.end() - m.start() - 1 if masked[m.end() - m.start() - 1] == "{" else 0)
    depth = 0
    for j in range(i, len(masked)):
        if masked[j] == "{":
            depth += 1
        elif masked[j] == "}":
            depth -= 1
            if depth == 0:
                return window[:j + 1]
    return None


# ---------------------------------------------------------------- 1. CSS
ART_BUILDERS = (r"function cardHtml\(n\)\s*\{", r"function d2jspArt\(n\)\s*\{", r"function artOr\(name, fallbackHtml, size\)\s*\{")
NO_FILTER = ("#tab-d2jsp .d2art-wrap", "#tab-d2jsp .d2art-wrap .d2art-img", "#tab-d2jsp .d2art-wrap:hover .d2art-img")
_STR_RE = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`")


def card_names(bible):
    """(classes, ids, prefixes) a D2JSP card or its art can carry, read from the markup builders
    (cardHtml, d2jspArt, artOr) and the #tab-d2jsp section that holds the list. Over-wide on
    purpose: a name that is only maybe on the card still counts as reaching it."""
    words = set()
    for pat in ART_BUILDERS:
        blk = _block(bible, pat) or ""
        for lit in _STR_RE.findall(blk):
            words.update(re.findall(r"[A-Za-z_][\w-]*", re.sub(r"\$\{[^}]*\}", " ", lit)))
    a = bible.find('<div class="tab-content" id="tab-d2jsp">')
    b = bible.find('<div class="tab-content"', a + 10) if a >= 0 else -1
    section = bible[a:b if b > a else a + 200000] if a >= 0 else ""
    for m in re.finditer(r"\b(?:class|id)\s*=\s*[\"']([^\"']*)[\"']", section):
        words.update(re.findall(r"[A-Za-z_][\w-]*", m.group(1)))
    words.update(("tab-content", "active", "tab-d2jsp", "d2jsp-list"))
    prefixes = set(w for w in words if w.endswith("-"))
    return words, prefixes


def _known(name, words, prefixes):
    return name in words or any(name.startswith(p) for p in prefixes)


def can_reach_card(selector, words, prefixes):
    """True when every compound of `selector` could match the card, its art or an ancestor.
    html, body and :root compounds are always reachable (their classes change at run time)."""
    sel = re.sub(r"::?[\w-]+(\((?:[^()]|\([^()]*\))*\))?", "", selector)   # pseudo-classes say when, not where
    sel = re.sub(r"\[[^\]]*\]", "", sel)                                     # attributes too
    for comp in re.split(r"\s*[>+~]\s*|\s+", sel.strip()):
        if not comp:
            continue
        tag = re.match(r"[A-Za-z*][\w-]*", comp)
        if tag and tag.group(0).lower() in ("html", "body"):
            continue
        for kind, name in re.findall(r"([.#])([\w-]+)", comp):
            if not _known(name, words, prefixes):
                return False
    return True


def css_problems(bible):
    bad = []
    rules = css_rules(bible)
    words, prefixes = card_names(bible)
    # Any !important filter that can reach the card wins over or ties with the no-filter rule,
    # whatever its specificity, so none is allowed (v3773 round 2, cases 1 and 2).
    for sels, decls in rules:
        for prop in ("filter", "-webkit-filter"):
            v = decls.get(prop)
            if not v or not v[1] or v[0] == "none":
                continue
            hit = [x for x in sels if x not in NO_FILTER and can_reach_card(x, words, prefixes)]
            if hit:
                bad.append("an !important %s can reach D2JSP card art: %s{%s:%s}" % (prop, hit[0], prop, v[0]))
    for pat in ART_BUILDERS:
        raw = _block(bible, pat) or ""
        for lit in _STR_RE.findall(raw):          # an inline style="filter:..." beats every sheet rule
            if re.search(r"(?<![\w-])(?:-webkit-)?filter\s*:", lit):
                bad.append("a D2JSP card builder writes an inline filter: %s" % lit[:120])
        if re.search(r"\.style\.(?:webkitF|f)ilter\b", code_mask(raw)):
            bad.append("a D2JSP card builder sets a filter in script (%s)" % pat)
        if re.search(r"setProperty\(\s*['\"](?:-webkit-)?filter['\"]", raw):
            bad.append("a D2JSP card builder sets a filter with setProperty (%s)" % pat)
    for sel in NO_FILTER:
        got = _decl(rules, sel, "filter")
        if ("none", True) not in got:
            bad.append("D2JSP card art can take a filter (%s): %s" % (sel, got))
    cv = _decl(rules, "#tab-d2jsp .d2jsp-card", "content-visibility")
    cis = _decl(rules, "#tab-d2jsp .d2jsp-card", "contain-intrinsic-size")
    if not any(v == "auto" for v, _i in cv):
        bad.append("a D2JSP card is not its own content-visibility:auto box: %s" % cv)
    if not any(v and v != "none" for v, _i in cis):
        bad.append("a contained D2JSP card has no intrinsic size, so the list jumps as it scrolls: %s" % cis)
    glow = _decl(rules, "#tab-d2jsp .d2art-wrap", "background")
    if not any("radial-gradient" in v and "--d2glow" in v for v, _i in glow):
        bad.append("D2JSP card art lost its baked glow: %s" % glow)
    return bad


# ---------------------------------------------------------------- 2-3. node
PRICE_FAKE = r"""
var WRITES = {};
function mkNode(card, kind){
  var n = { _t: '', hidden: false, disabled: false, kind: kind, card: card };
  Object.defineProperty(n, 'textContent', { get: function(){ return this._t; },
    set: function(v){ WRITES[card.name] = (WRITES[card.name] || 0) + 1; this._t = String(v); } });
  n.closest = function(){ return card; };
  return n;
}
var CARDS = [];
for (var i = 0; i < 50; i++) {
  var c = { name: 'item' + i, attrs: {} };
  c.getAttribute = function(k){ return k === 'data-d2jsp-item' ? this.name : this.attrs[k]; };
  c.setAttribute = function(k, v){ this.attrs[k] = v; };
  c.removeAttribute = function(k){ delete this.attrs[k]; };
  c.price = mkNode(c, 'price'); c.post = mkNode(c, 'post'); c.sold = mkNode(c, 'sold');
  c.draft = mkNode(c, 'draft'); c.wait = mkNode(c, 'wait');
  c.querySelector = function(sel){
    if (sel === '[data-d2jsp-price]') return this.price;
    if (sel === '[data-d2jsp-post]') return this.post;
    if (sel === '[data-d2jsp-sold]') return this.sold;
    if (sel === '[data-d2jsp-draft]') return this.draft;
    if (sel === '[data-d2jsp-wait]') return this.wait;
    return null;
  };
  CARDS.push(c);
}
var document = { querySelectorAll: function(sel){
  if (sel === '#d2jsp-list .d2jsp-card') return CARDS.slice();
  if (sel === '#d2jsp-list [data-d2jsp-price]') return CARDS.map(function(c){ return c.price; });
  return [];
} };
var quoted = {}, pending = {}, reading = false;
function priceText(n){ return quoted[n] ? ('fg ' + quoted[n].fg) : 'Public price unknown.'; }
function d2jspPriceToSend(fg, typed){ return fg == null ? null : fg; }
function sendOf(n){ return d2jspPriceToSend((quoted[n] || {}).fg, typedOf(n)); }   /* #113 - the card's post price (board-checked in the page) */
function typedOf(){ return ''; }
function soldOf(){ return false; }
function tradeView(){ return { held: true, live: 1, listed: 0, slots: [], traded: 0, total: 1, all: false, pick: false, legacy: false, sold: false }; }   /* REG-2883 */
function markWord(){ return 'Mark traded'; }
function baseOf(){ return ''; }
function modsOf(){ return ''; }
function copiesOf(){ return 1; }
function d2jspItemBlock(){ return { ok: false, body: '' }; }
function quoteFresh(){ return false; }
var fetch = function(){ return Promise.resolve({ json: function(){ return { fg: 9, reason: 'read' }; } }); };
"""


def node_problems(bible):
    if not NODE:
        return ["node is not on this machine"]
    bad = []
    paint_prices = _block(bible, r"function paintPrices\s*\(")
    ask = _block(bible, r"function ask\s*\(\s*name\s*,\s*done\s*,\s*force\s*\)")
    if not paint_prices or not ask:
        return ["the D2JSP price painter is not in bible.html"]
    prog = PRICE_FAKE + paint_prices + "\n" + ask + r"""
ask('item7', function(){
  setTimeout(function(){
    var touched = Object.keys(WRITES);
    console.log(JSON.stringify({ touched: touched.length, names: touched.slice(0, 3), fg: quoted.item7 && quoted.item7.fg }));
  }, 0);
});
"""
    try:
        got = _node(prog)
        if got.get("touched") != READING_CARDS or got.get("names") != ["item7"] or got.get("fg") != 9:
            bad.append("one D2JSP reading repainted %s of 50 cards (budget %d): %s"
                       % (got.get("touched"), READING_CARDS, json.dumps(got)))
    except Exception as e:
        bad.append("the one-card reading check raised %s" % e)
    planner = _block(bible, r"window\._d2jspPlannerPaint\s*=\s*function\s*\(\s*\)")
    if not planner:
        bad.append("the D2JSP Options painter is not in bible.html")
    else:
        prog = r"""
var PAINTS = 0, HTMLS = 0;
function paint(){ PAINTS++; }
var window = { _cbHostHtml: function(){ return '<div class="cb-modal">picker</div>'; } };
var HOST = { hidden: true, _h: '', firstChild: null, _v3773html: undefined,
  querySelector: function(){ return null; } };
Object.defineProperty(HOST, 'innerHTML', { get: function(){ return this._h; },
  set: function(v){ HTMLS++; this._h = v; this.firstChild = v ? {} : null; } });
function plannerHost(){ return HOST; }
""" + planner + r""";
window._d2jspPlannerPaint(); window._d2jspPlannerPaint(); window._d2jspPlannerPaint();
console.log(JSON.stringify({ paints: PAINTS, htmls: HTMLS, shown: HOST.hidden === false }));
"""
        try:
            got = _node(prog)
            if got.get("paints") != 0 or got.get("htmls") != 1 or not got.get("shown"):
                bad.append("Options repaints the D2JSP list or rebuilds the same picker: %s" % json.dumps(got))
        except Exception as e:
            bad.append("the Options paint check raised %s" % e)
    desk = _block(bible, r"function _cbPickListHtml\s*\(\s*\)")
    if not desk or "var _cbDeskList" not in bible:
        bad.append("the D2JSP desk does not keep its builder list")
    else:
        prog = r"""
var BUILDS = 0;
var _cbDeskList = { key: null, html: '' };
var st = { pick: { qt: 'u', rail: 0, node: null, q: '', filt: '' }, host: { desk: 'd2jsp' } };
function _cbListSlot(){ return 'helm'; }
function _cbDb(){ return true; }
function _cbPickRows(){ return [1, 2, 3]; }
function _cbListHtml(rows){ BUILDS++; return 'list' + BUILDS + ':' + st.pick.q; }
""" + desk + r"""
var a = _cbPickListHtml(), b = _cbPickListHtml(), c = _cbPickListHtml();
var desk = BUILDS;
st.pick.q = 'shako';
var d = _cbPickListHtml();
var query = BUILDS - desk;
st.host = { desk: 'planner' };
var b0 = BUILDS; _cbPickListHtml(); _cbPickListHtml();
console.log(JSON.stringify({ desk: desk, same: a === b && b === c, query: query, fresh: d.indexOf('shako') >= 0,
  other: BUILDS - b0 }));
"""
        try:
            got = _node(prog)
            if got.get("desk") != 1 or not got.get("same"):
                bad.append("the D2JSP desk rebuilds its builder list on every Options click: %s" % json.dumps(got))
            if got.get("query") != 1 or not got.get("fresh"):
                bad.append("a new search on the D2JSP desk shows the old list: %s" % json.dumps(got))
            if got.get("other") != 2:
                bad.append("a builder host other than the D2JSP desk reuses a list: %s" % json.dumps(got))
        except Exception as e:
            bad.append("the desk list check raised %s" % e)
    return bad


# ---------------------------------------------------------------- 4a. Chrome
PROBE = r"""
(function(){
  var held = [];
  window.__quoteHeld = held;
  var f = window.fetch;
  window.fetch = function(url){
    if (String(url).indexOf('d2jsp_quote') >= 0 && window.__holdQuotes) {
      return new Promise(function(res){
        held.push(function(){
          res(new Response(JSON.stringify({fg: 7, low: 5, high: 9, n: 3, readAt: new Date().toISOString(), reason: 'read'}),
                           {headers: {'Content-Type': 'application/json'}}));
        });
      });
    }
    return f.apply(window, arguments);
  };
})();
window.__d2seed = function(n){
  var names = Object.keys(D2IO_ART).filter(function(k){ return k && !/^base_|^rune_/i.test(k) && /^[A-Z]/.test(k); }).slice(0, n);
  var gear = {};
  names.forEach(function(k){ gear[k] = {}; });
  var S = (typeof LS !== 'undefined' && LS && LS.setItem) ? LS : localStorage;
  S.setItem('d2r_d2jsp_gear', JSON.stringify(gear));
  return names.length;
};
window.__d1 = async function(rooms, n){
  function frames(){ return new Promise(function(r){ requestAnimationFrame(function(){ requestAnimationFrame(function(){ r(); }); }); }); }
  function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
  var gcs = window.__realGCS || window.getComputedStyle;
  var out = {error: null, seeded: 0, rooms: {}, reading: null, options: []};
  try {
    out.seeded = window.__d2seed(n);
    window.__holdQuotes = true;
    switchTab('d2jsp');
    for (var w = 0; w < 80 && document.querySelectorAll('#d2jsp-list .d2jsp-card').length < out.seeded - 2; w++) await sleep(100);
    await frames();
    out.cards = document.querySelectorAll('#d2jsp-list .d2jsp-card').length;
    function contained(el, root){
      for (var p = el; p && p !== root; p = p.parentElement)
        if (gcs(p).contentVisibility === 'auto' && p.getElementsByTagName('*').length <= 400) return true;
      return false;
    }
    for (var r = 0; r < rooms.length; r++) {
      switchTab(rooms[r]);
      await frames();
      var root = document.getElementById('tab-' + rooms[r]);
      var all = root ? root.getElementsByTagName('*') : [];
      var bad = 0, tot = 0, inCard = 0;
      for (var i = 0; i < all.length; i++) {
        var fl = gcs(all[i]).filter;            /* any filter at all: WebKitGTK paints every one in software */
        if (!fl || fl === 'none') continue;
        tot++;
        if (all[i].closest('.d2jsp-card')) inCard++;
        if (!contained(all[i], root)) bad++;
      }
      out.rooms[rooms[r]] = {filtered: tot, uncontained: bad, inCard: inCard, nodes: all.length};
    }
    switchTab('d2jsp');
    await frames();
    var list = document.getElementById('d2jsp-list');
    for (var w2 = 0; w2 < 50 && !window.__quoteHeld.length; w2++) await sleep(100);
    var buf = [];
    var mo = new MutationObserver(function(rs){ buf.push.apply(buf, rs); });
    mo.observe(list, {subtree: true, childList: true, characterData: true, attributes: true});
    function take(){ var rs = buf.concat(mo.takeRecords()); buf = []; return rs; }
    function cardsOf(rs, host){
      var set = new Set();
      rs.forEach(function(x){
        if (host && host.contains(x.target)) return;
        var t = x.target.nodeType === 1 ? x.target : x.target.parentElement;
        var c = t && t.closest && t.closest('.d2jsp-card');
        /* A status line or the list itself is not a card. The budget is cards. */
        if (c) set.add(c.getAttribute('data-d2jsp-item'));
      });
      return set.size;
    }
    /* v3856 - WAIT FOR THE LIST TO GO QUIET BEFORE THE HELD READING IS RELEASED. Under full-gate load the
       228-card list was still painting (late art, deferred rows) when the reading landed, and those
       paints were counted as the reading's: 3 cards against a budget of 1, green when run alone. Five
       quiet 100 ms windows in a row (up to 10 s) is the list at rest; the budget itself is unchanged. */
    for (var qw = 0, calm = 0; qw < 100 && calm < 5; qw++) { await sleep(100); calm = take().length ? 0 : calm + 1; }
    out.quietBeforeReading = calm >= 5;
    take();
    var heldN = window.__quoteHeld.length;
    var one = window.__quoteHeld.shift();
    if (one) one();
    await sleep(300); await frames();
    out.reading = {held: heldN, cards: cardsOf(take())};
    window.__holdQuotes = false;
    while (window.__quoteHeld.length) window.__quoteHeld.shift()();
    for (var q = 0, still = 0; q < 100 && still < 5; q++) { await sleep(200); still = take().length ? 0 : still + 1; }
    for (var k = 0; k < 2; k++) {
      take();
      var b = document.querySelector('#d2jsp-list [data-d2jsp-options]');
      var t0 = performance.now();
      if (b) b.click();
      var sync = performance.now() - t0;
      await frames();
      var host = document.getElementById('d2jsp-planner-host');
      out.options.push({sync_ms: Math.round(sync), paint_ms: Math.round(performance.now() - t0),
                        cards: cardsOf(take(), host), open: !!(host && !host.hidden)});
      if (window._d2jspPlannerClose) window._d2jspPlannerClose();
      await frames();
      await sleep(200);
    }
    mo.disconnect();
  } catch (e) { out.error = String(e && e.stack || e); }
  return out;
};
"""


def _serve(blobs, quote_delay=0.1):
    """Board blobs by ?v=, repo files, a stub d2jsp quote, and a /__report sink. -> (httpd, port, reports)"""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    reports = []
    types = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css",
             ".json": "application/json", ".png": "image/png", ".webp": "image/webp",
             ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".gif": "image/gif"}

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, ctype):
            self.send_response(200)
            if ctype:
                self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n)
            if self.path.startswith("/__report"):
                try:
                    reports.append(dict(json.loads(body.decode("utf-8", "replace")), _t=time.time()))
                except Exception:
                    pass
            self._send(b"{}", "application/json")

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/bible.html":
                key = (urllib.parse.parse_qs(parsed.query).get("v") or ["fix"])[0]
                if key not in blobs:
                    self.send_error(404)
                    return
                self._send(blobs[key], types[".html"])
                return
            if parsed.path.endswith("/api/d2jsp_quote"):
                time.sleep(quote_delay)
                self._send(json.dumps({"fg": None, "low": None, "high": None, "n": 0,
                                       "readAt": "2026-10-19T00:00:00.000Z", "reason": "no prices"}).encode(),
                           "application/json")
                return
            if parsed.path.startswith("/api/"):
                self.send_error(404)
                return
            path = os.path.normpath(os.path.join(ROOT, urllib.parse.unquote(parsed.path).lstrip("/")))
            if os.path.commonpath([ROOT, path]) != ROOT or not os.path.isfile(path):
                self.send_error(404)
                return
            with open(path, "rb") as fh:
                self._send(fh.read(), types.get(os.path.splitext(path)[1].lower()))

        def log_message(self, fmt, *args):
            return

    class Quiet(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            return

    port = _free_port(17961)
    httpd = Quiet(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port, reports


def chrome_run(blobs, keys):
    from test_v3769_vault_move_list_visual import _chrome_path, _wait_fn
    chrome = _chrome_path()
    if not chrome:
        raise RuntimeError(NO_BROWSER)
    httpd, port, _reports = _serve(blobs)
    udd = tempfile.mkdtemp(prefix="v3773-d1-")
    browser = None
    out = {}
    try:
        browser = _chrome_proc(chrome, udd, _free_port(port + 1))
        cport = int(re.search(r"--remote-debugging-port=(\d+)", " ".join(browser.args)).group(1))
        for key in keys:
            cdp = _connect(_new_tab(cport)["webSocketDebuggerUrl"])
            try:
                cdp.call("Page.enable")
                cdp.call("Runtime.enable")
                cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": PROBE})
                cdp.call("Emulation.setDeviceMetricsOverride",
                         {"width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False})
                cdp.call("Page.navigate", {"url": "http://127.0.0.1:%d/bible.html?v=%s" % (port, key)})
                _wait_fn(cdp, "typeof window.switchTab==='function' && typeof window.D2IO_ART==='object'", timeout=120)
                out[key] = _ev_async(cdp, "window.__d1(%s, %d)" % (json.dumps(list(ROOMS + REPORT_ROOMS)), CARDS),
                                     timeout=300)
            finally:
                cdp.close()
        return out
    finally:
        if browser and browser.poll() is None:
            browser.terminate()
            try:
                browser.wait(timeout=5)
            except Exception:
                browser.kill()
        httpd.shutdown()
        shutil.rmtree(udd, ignore_errors=True)


def chrome_problems(got):
    bad = []
    if got.get("error"):
        return ["the Chrome D2JSP probe raised %s" % got["error"]]
    if (got.get("cards") or 0) < CARDS - 2:
        bad.append("the D2JSP list drew %s of %d synthetic filings" % (got.get("cards"), CARDS))
    for room in ROOMS:
        row = (got.get("rooms") or {}).get(room) or {}
        if row.get("uncontained") is None or row["uncontained"] > FILTER_BUDGET[room]:
            bad.append("%s paints %s filtered elements outside a contained card (budget %d)" % (room, row.get("uncontained"), FILTER_BUDGET[room]))
    d2 = (got.get("rooms") or {}).get("d2jsp") or {}
    if d2.get("inCard") is None or d2["inCard"] > CARD_FILTERS:
        bad.append("%s elements inside D2JSP cards compute a filter (budget %d)" % (d2.get("inCard"), CARD_FILTERS))
    reading = got.get("reading") or {}
    if not got.get("quietBeforeReading"):
        bad.append("the D2JSP list never went quiet before the held reading was released, so its count is not the reading's")
    if not reading.get("held") or reading.get("cards") is None or reading["cards"] > READING_CARDS:
        bad.append("one D2JSP reading touched %s cards (budget %d)" % (reading.get("cards"), READING_CARDS))
    opts = got.get("options") or []
    if len(opts) != 2 or not all(o.get("open") for o in opts):
        bad.append("Options did not open twice: %s" % opts)
    for i, o in enumerate(opts):
        if o.get("cards", 999) > OPTIONS_CARDS:
            bad.append("Options open %d repainted %s D2JSP cards (budget %d)" % (i + 1, o.get("cards"), OPTIONS_CARDS))
    return bad


# ---------------------------------------------------------------- 4b. WebKitGTK
WK_JS = r"""
(function(){
  if (location.pathname !== '/bible.html') return;
  function rep(o){ try { var x = new XMLHttpRequest(); x.open('POST', '/__report', true); x.send(JSON.stringify(o)); } catch (e) {} }
  var IV = 50, last = performance.now(), blocked = 0, worst = 0;
  setInterval(function(){
    var now = performance.now(), late = now - last - IV;
    if (late > 0) { blocked += late; if (late > worst) worst = late; }
    last = now;
  }, IV);
  function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
  async function phase(name, ms, fn){
    blocked = 0; worst = 0;
    var t0 = performance.now(), extra = {};
    if (fn) { try { extra = (await fn()) || {}; } catch (e) { extra = {error: String(e)}; } }
    while (performance.now() - t0 < ms) await sleep(100);
    var wall = performance.now() - t0;
    rep(Object.assign({phase: name, wall_ms: Math.round(wall), blocked_ms: Math.round(blocked),
                       blocked_pct: Math.round(100 * blocked / wall), worst: Math.round(worst)}, extra));
  }
  window.addEventListener('load', function(){
    (async function(){
      for (var w = 0; w < 600 && !(typeof switchTab === 'function' && typeof D2IO_ART === 'object'); w++) await sleep(100);
      var names = Object.keys(D2IO_ART).filter(function(k){ return k && !/^base_|^rune_/i.test(k) && /^[A-Z]/.test(k); }).slice(0, __N__);
      var gear = {};
      names.forEach(function(k){ gear[k] = {}; });
      var S = (typeof LS !== 'undefined' && LS && LS.setItem) ? LS : localStorage;
      S.setItem('d2r_d2jsp_gear', JSON.stringify(gear));
      switchTab('session');
      await phase('idle', 4000);
      await phase('d2jsp-open', 6000, function(){
        var t0 = performance.now(); switchTab('d2jsp');
        return {switch_ms: Math.round(performance.now() - t0), cards: document.querySelectorAll('#d2jsp-list .d2jsp-card').length};
      });
      await phase('price-refresh', 6000);
      for (var k = 1; k <= 2; k++) {
        await phase('options-' + k, 4000, function(){
          var b = document.querySelector('#d2jsp-list [data-d2jsp-options]');
          var t0 = performance.now(); if (b) b.click();
          return {sync_ms: Math.round(performance.now() - t0), opened: !!b};
        });
        try { if (window._d2jspPlannerClose) window._d2jspPlannerClose(); } catch (e) {}
      }
      rep({phase: 'done'});
    })();
  });
})();
"""

WK_PY = r"""
import gi, os, sys
gi.require_version('Gtk', '3.0')
try:
    gi.require_version('WebKit2', '4.1')
except ValueError:
    gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, WebKit2, GLib
prof, js, url, dur = sys.argv[1], open(sys.argv[2]).read(), sys.argv[3], int(sys.argv[4])
dm = WebKit2.WebsiteDataManager(base_data_directory=prof + '/data', base_cache_directory=prof + '/cache')
ctx = WebKit2.WebContext.new_with_website_data_manager(dm)
ucm = WebKit2.UserContentManager()
ucm.add_script(WebKit2.UserScript.new(js, WebKit2.UserContentInjectedFrames.TOP_FRAME,
                                      WebKit2.UserScriptInjectionTime.START, None, None))
wv = WebKit2.WebView(web_context=ctx, user_content_manager=ucm)
win = Gtk.Window(); win.set_default_size(1440, 900); win.add(wv); win.show_all()
wv.load_uri(url)
GLib.timeout_add_seconds(dur, lambda: (Gtk.main_quit(), False)[1])
Gtk.main()
"""


def webkit_available():
    if not shutil.which("xvfb-run"):
        return False
    probe = ("import gi\ngi.require_version('Gtk','3.0')\n"
             "try:\n gi.require_version('WebKit2','4.1')\nexcept ValueError:\n gi.require_version('WebKit2','4.0')\n"
             "from gi.repository import WebKit2\n")
    try:
        return subprocess.run([sys.executable, "-c", probe], capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False


def _descendants(pid):
    kids = {}
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            with open("/proc/%s/stat" % d) as fh:
                ppid = int(fh.read().rsplit(")", 1)[1].split()[1])
        except Exception:
            continue
        kids.setdefault(ppid, []).append(int(d))
    out, todo = [], [pid]
    while todo:
        p = todo.pop()
        for c in kids.get(p, []):
            out.append(c)
            todo.append(c)
    return out


def _rss_kb(pid):
    try:
        with open("/proc/%d/comm" % pid) as fh:
            if not fh.read().startswith("WebKitWebProces"):
                return None
        with open("/proc/%d/status" % pid) as fh:
            for ln in fh:
                if ln.startswith("VmRSS:"):
                    return int(ln.split()[1])
    except Exception:
        return None
    return None


def webkit_run(blob, dur=60):
    """One guarded WebKitGTK run of the D2JSP phases. -> dict"""
    httpd, port, reports = _serve({"run": blob})
    tmp = tempfile.mkdtemp(prefix="v3773-wk-")
    js = os.path.join(tmp, "probe.js")
    py = os.path.join(tmp, "wk.py")
    with open(js, "w", encoding="utf-8") as fh:
        fh.write(WK_JS.replace("__N__", str(CARDS)))
    with open(py, "w", encoding="utf-8") as fh:
        fh.write(WK_PY)
    url = "http://127.0.0.1:%d/bible.html?v=run&app=1#session" % port   # app=1: the console window's own mode
    proc = subprocess.Popen(["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", sys.executable, py,
                             os.path.join(tmp, "prof"), js, url, str(dur)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    samples, killed, peak = [], None, 0
    t0 = time.time()
    try:
        while proc.poll() is None and time.time() - t0 < dur + 30:
            time.sleep(0.5)
            for p in _descendants(proc.pid):   # only this run's own tree; his console is never read
                kb = _rss_kb(p)
                if kb is None:
                    continue
                samples.append((round(time.time() - t0, 1), kb))
                peak = max(peak, kb)
                if kb > WK_KILL_KB:
                    killed = "the 3 GB guard killed the web process at %d MB" % (kb // 1024)
            if killed or any(r.get("phase") == "done" for r in reports):
                break
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
            proc.wait(timeout=10)
        httpd.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    phases = {r["phase"]: r for r in reports if r.get("phase")}
    idle_at = phases.get("idle", {}).get("_t")
    base = None
    if idle_at:
        before = [kb for t, kb in samples if t0 + t <= idle_at]
        base = before[-1] if before else None
    return {"phases": phases, "killed": killed, "peak_mb": peak // 1024,
            "idle_mb": None if base is None else base // 1024, "samples": len(samples)}


def webkit_problems(got):
    bad = []
    if got.get("killed"):
        bad.append(got["killed"])
    phases = got.get("phases") or {}
    for name in ("idle", "d2jsp-open", "price-refresh", "options-1", "options-2", "done"):
        if name not in phases:
            bad.append("WebKit never reported %s (the page stopped answering)" % name)
    for name, row in phases.items():
        if name in ("done", "idle"):   # idle is the boot baseline, reported not judged
            continue
        if row.get("blocked_pct") is None or row["blocked_pct"] > WK_BLOCKED_PCT:
            bad.append("WebKit %s blocked the main thread %s%% (budget %d%%)" % (name, row.get("blocked_pct"), WK_BLOCKED_PCT))
    if got.get("idle_mb") is None:
        bad.append("WebKit memory was not sampled at idle")
    elif got["peak_mb"] - got["idle_mb"] > WK_RSS_GROWTH_MB:
        bad.append("the WebKit web process grew %d MB over idle (budget %d)" % (got["peak_mb"] - got["idle_mb"], WK_RSS_GROWTH_MB))
    if (phases.get("d2jsp-open") or {}).get("cards", 0) < CARDS - 2:
        bad.append("WebKit drew %s of %d D2JSP cards" % ((phases.get("d2jsp-open") or {}).get("cards"), CARDS))
    return bad


class TestD2jspCardsStayCheap(unittest.TestCase):
    def test_01_card_art_has_no_filter_and_each_card_is_contained(self):
        bad = css_problems(_read())
        self.assertEqual(bad, [], bad)

    def test_02_a_reading_repaints_its_own_card_and_options_keeps_the_list(self):
        bad = node_problems(_read())
        self.assertEqual(bad, [], bad)

    def test_03_chrome_counts_filtered_art_and_touched_cards(self):
        if "heart2." in os.path.abspath(__file__):
            return
        with open(BIBLE, "rb") as fh:
            blob = fh.read()
        try:
            got = chrome_run({"fix": blob}, ["fix"])["fix"]
        except RuntimeError as exc:
            if str(exc) == NO_BROWSER:
                SKIPS.add(NO_BROWSER)
                return
            raise
        print("chrome", json.dumps({k: got.get(k) for k in ("cards", "rooms", "reading", "options")}))
        bad = chrome_problems(got)
        self.assertEqual(bad, [], bad)

    def test_04_webkitgtk_opens_d2jsp_refreshes_and_opens_options_under_budget(self):
        if "heart2." in os.path.abspath(__file__):
            return
        if not webkit_available():
            SKIPS.add(NO_WEBKIT)
            return
        with open(BIBLE, "rb") as fh:
            got = webkit_run(fh.read())
        print("webkit", json.dumps(got))
        bad = webkit_problems(got)
        self.assertEqual(bad, [], bad)

    def test_05_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = "d2jsp cards stay cheap: %d distinct attacks, wilson %.4f vs vault.apply bar %.3f" % (n, w, bar)
        self.assertGreaterEqual(n, 10, msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar, msg)


RED_PROOF = [
    # Every entry changes what the page does; the CSS rule reader or a node run catches it in heart2.
    {"why": "D2JSP card art takes the global drop-shadow again (the img is dropped from the no-filter rule).",
     "file": "bible.html",
     "find": "#tab-d2jsp .d2art-wrap,#tab-d2jsp .d2art-wrap .d2art-img,#tab-d2jsp .d2art-wrap:hover .d2art-img{filter:none!important;",
     "replace": "#tab-d2jsp .d2art-wrap,#tab-d2jsp .d2art-wrap:hover .d2art-img{filter:none!important;",
     "matches": 1},
    {"why": "Hovering a D2JSP card turns the software drop-shadow back on.",
     "file": "bible.html",
     "find": "#tab-d2jsp .d2art-wrap,#tab-d2jsp .d2art-wrap .d2art-img,#tab-d2jsp .d2art-wrap:hover .d2art-img{filter:none!important;",
     "replace": "#tab-d2jsp .d2art-wrap,#tab-d2jsp .d2art-wrap .d2art-img{filter:none!important;",
     "matches": 1},
    {"why": "Review case 1: a higher-specificity !important rule gives every D2JSP card img a drop-shadow and saturate.",
     "file": "bible.html",
     "find": "transition:none!important} /* v3773 no art filter */",
     "replace": "transition:none!important} /* v3773 no art filter */\n"
                "#tab-d2jsp #d2jsp-list .d2jsp-card .d2art-wrap img.d2art-img{filter:drop-shadow(0 0 6px #f0c060) saturate(1.4)!important}",
     "matches": 1},
    {"why": "Review case 2: the wrap leaves the no-filter rule, so the global .d2art-wrap saturate/contrast filter is back on every card.",
     "file": "bible.html",
     "find": "#tab-d2jsp .d2art-wrap,#tab-d2jsp .d2art-wrap .d2art-img,#tab-d2jsp .d2art-wrap:hover .d2art-img{filter:none!important;",
     "replace": "#tab-d2jsp .d2art-wrap .d2art-img,#tab-d2jsp .d2art-wrap:hover .d2art-img{filter:none!important;",
     "matches": 1},
    {"why": "An inline !important filter on the card's art box beats every sheet rule.",
     "file": "bible.html",
     "find": "      + '<div class=\"d2jsp-art\">' + art + '</div>'",
     "replace": "      + '<div class=\"d2jsp-art\" style=\"filter:saturate(1.4)!important\">' + art + '</div>'",
     "matches": 1},
    {"why": "A D2JSP card is painted even when it is off screen.",
     "file": "bible.html",
     "find": "#tab-d2jsp .d2jsp-card{content-visibility:auto;",
     "replace": "#tab-d2jsp .d2jsp-card{content-visibility:visible;",
     "matches": 1},
    {"why": "A contained D2JSP card has no intrinsic size, so the scroll bar jumps.",
     "file": "bible.html",
     "find": "content-visibility:auto;contain-intrinsic-size:auto 230px} /* v3773 contained card */",
     "replace": "content-visibility:auto} /* v3773 contained card */",
     "matches": 1},
    {"why": "A finished reading repaints every card.",
     "file": "bible.html",
     "find": "      paintPrices(name);\n      if (done) done();",
     "replace": "      paintPrices();\n      if (done) done();",
     "matches": 1},
    {"why": "paintPrices ignores the card it was given and walks the whole list.",
     "file": "bible.html",
     "find": "    if (only != null) {\n      var one = [];",
     "replace": "    if (false) {\n      var one = [];",
     "matches": 1},
    {"why": "Options repaints the whole D2JSP list under the picker.",
     "file": "bible.html",
     "find": "    return true; /* v3773 no list repaint under the picker */",
     "replace": "    paint();\n    return true; /* v3773 no list repaint under the picker */",
     "matches": 1},
    {"why": "Options rebuilds the same picker markup on every paint.",
     "file": "bible.html",
     "find": "if (!(host._v3773html === _hostHtml && host.firstChild))",
     "replace": "if (true)",
     "matches": 1},
    {"why": "The D2JSP desk rebuilds its 1,220-row builder list on every Options click.",
     "file": "bible.html",
     "find": "    if (_cbDeskList.key === key) return _cbDeskList.html; /* v3773 cached desk list */\n",
     "replace": "",
     "matches": 1},
    {"why": "A new search on the D2JSP desk keeps the old list (the query left the key).",
     "file": "bible.html",
     "find": "p.node, p.q || '', p.filt || ''",
     "replace": "p.node, p.filt || ''",
     "matches": 1},
    {"why": "Every builder host reuses one list, so the planner shows the desk's rows.",
     "file": "bible.html",
     "find": "    if (!(p && st.host && st.host.desk === 'd2jsp')) return _cbListHtml(_cbPickRows());\n",
     "replace": "",
     "matches": 1},
]


def measure_main():
    """Before/after on v3771 (69817adf) and the working tree: Chrome counts, then WebKitGTK
    one board at a time under the 3 GB guard."""
    blobs = {"v3771": subprocess.check_output(["git", "show", "69817adf:bible.html"], cwd=ROOT),
             "fix": open(BIBLE, "rb").read()}
    out = {}
    try:
        out["chrome"] = chrome_run(blobs, ["v3771", "fix"])
    except RuntimeError as exc:
        out["chrome"] = {"skip": str(exc)}
    if webkit_available():
        out["webkit"] = {k: webkit_run(blobs[k]) for k in ("v3771", "fix")}
    else:
        out["webkit"] = {"skip": NO_WEBKIT}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    if "--measure" in sys.argv:
        raise SystemExit(measure_main())
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestD2jspCardsStayCheap)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    for s in sorted(SKIPS):
        print(s)
    if SKIPS:
        sys.exit(77)
