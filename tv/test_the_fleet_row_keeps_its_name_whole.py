# -*- coding: utf-8 -*-
"""REG-1613 — A FLEET ROW KEEPS ITS PC'S NAME WHOLE, AND ITS EXCEPTION WORDS NEVER PRINT OVER EACH OTHER.

MEASURED 2026-09-30, the fleet rail at 1120 and 901 with the render gate's own stub roster: "K o n y o" and "L a p t o p"
one letter a line, and "picker broken" printed through "Claude signed". His console showed the milder form the same
minute (his screenshot at 19:55): every online row carried "river stuck", the verdict pushed a line down. The cause
was structural: each word (river stuck · picker short · Claude signed out) was its own grid item with nowrap and no
column, so auto-placement put them in the `auto` tracks, which grow to full width before the name's 1fr gets
anything. The render gate called it green - "painted 27/27 · clipped 0/99 · covered 0/27" - because a word painted
on top of another word is still painted, and a name one letter wide is not clipped. The instrument asked the wrong
question; this law asks the right one, from the characters' own rects:
  1. no NAME breaks inside a word (its line boxes never outnumber its words),
  2. no two words of a row overlap (name, each exception word, the verdict - text ink, via Ranges),
  3. nothing runs past the rail's right edge,
at four widths, over a scratch localhost server with the shipped page and a stubbed /api/fleet. PREMISE: every
exception word was drawn. [[visual-regression-detector]] [[feedback-suspect-the-instrument]] RED_PROOF below.
"""
import json
import os
import socket
import subprocess
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _free_port():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


# ⚠ BEFORE the import: render_check reads its Chrome port once. Never 9222/9223 (his).
_LAW_PORT = os.environ.get("TV_LAW_PORT", "").strip()
os.environ["TV_RENDER_PORT"] = _LAW_PORT if _LAW_PORT.isdigit() and _LAW_PORT not in ("9222", "9223") else str(_free_port())
import render_check as RC  # noqa: E402

WIDTHS = ((1440, 1000), (1280, 800), (1120, 628), (901, 900))

RED_PROOF = [
    {
        "why": "REG-1613 - the exception words lose their own line: auto-placed into the rail's tracks, the name is squeezed",
        "file": "control_ui.html",
        "find": "  .fleet-row > .fleet-chips { grid-column: 2 / -1; display: flex; flex-wrap: wrap; align-items: baseline;\n",
        "replace": "  .fleet-row > .fleet-chips { display: flex; flex-wrap: wrap; align-items: baseline;\n",
        "matches": 1,
    },
    {
        "why": "REG-1613 - each word is its own grid item again, auto-placed into the rail's narrow tracks: the squeeze that broke the names",
        "file": "control_ui.html",
        "find": "    return s ? '<span class=\"fleet-chips\">' + s + '</span>' : '';\n",
        "replace": "    return s;\n",
        "matches": 1,
    },
]

H = 3600
#: every exception word at once, on the names that broke: two words on one row, three on another, a long name
_STUCK = {"river": {"stuck": [{"station": "EMPTY", "n": 243, "oldestS": 50 * H, "why": "route shut until this PC proves its own gates"}]}}
_OUT = {"claude": {"state": "off", "needsLogin": True, "why": "OAuth session expired - run claude, type /login"},
        "grok": {"state": "off", "needsLogin": True, "why": "Grok is not signed in on this PC"}}
_ON = {"claude": {"state": "on", "needsLogin": False, "why": "read 1 min ago"}, "grok": {"state": "off", "needsLogin": False, "why": "off"}}
_BROKEN = {"ok": False, "broken": True, "slot": "tors", "label": "Body Armor", "why": "the builder database would not parse"}


def _fleet():
    t = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - 40))
    presence = {"state": "online", "via": "beacon", "ageS": 40, "words": "", "staleAfterS": 2040}
    online = [
        {"machine": "box-mac", "nickname": "Konyo", "ver": "v3531", "t": t, "system": _STUCK, "readers": _ON},
        {"machine": "box-alt", "nickname": "Konyo ALT TEST", "ver": "v3531", "t": t, "system": _STUCK,
         "readers": _OUT, "picker": _BROKEN},
        {"machine": "box-lap", "nickname": "Laptop", "ver": "v3531", "t": t, "readers": _OUT, "picker": _BROKEN},
        {"machine": "box-gb", "nickname": "GrokBot", "ver": "v3531", "t": t, "system": _STUCK, "readers": _ON}]
    for row in online:
        row["presence"] = dict(presence)
    return {"ok": True, "me": "box-mac", "publishedVer": "v3531", "fromCache": False, "staleAgeS": 0.0, "webOnly": [],
            "online": online,
            "offline": [{"machine": "box-wife", "nickname": "Wife PC", "ver": "v2101"}]}


SEED = r"""(function(){
  var FLEET = %s, _f = window.fetch;
  window.fetch = function(u, o){
    var s = String(u && u.url || u);
    if (s.indexOf('/api/fleet') === 0 && s.indexOf('/api/fleet_compare') !== 0)
      return Promise.resolve(new Response(JSON.stringify(FLEET), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    if (s.indexOf('/api/') === 0)
      return Promise.resolve(new Response(JSON.stringify({ ok: false, why: 'law page - no console behind it' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    return _f.apply(this, arguments);
  };
  var l = document.getElementById('fleet-list'); if (l) l.innerHTML = '';
  if (window._fleetRefresh) window._fleetRefresh();
  return 1; })()"""

MEASURE = r"""(function(){ try {
  var l = document.getElementById('fleet-list'); if (!l) return JSON.stringify({ err: 'no #fleet-list' });
  var lr = l.getBoundingClientRect();
  function ink(el){ var out = [], tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), n;
    while ((n = tw.nextNode())) { if (!n.data.trim()) continue; var rg = document.createRange(); rg.selectNodeContents(n);
      [].forEach.call(rg.getClientRects(), function(r){ if (r.width > 0.5 && r.height > 0.5) out.push({l: r.left, t: r.top, r: r.right, b: r.bottom}); }); }
    return out; }
  function lines(rs){ var tops = []; rs.forEach(function(r){ if (!tops.some(function(t){ return Math.abs(t - r.t) < 3; })) tops.push(r.t); }); return tops.length; }
  function hit(a, b){ return Math.min(a.r, b.r) - Math.max(a.l, b.l) > 1 && Math.min(a.b, b.b) - Math.max(a.t, b.t) > 1; }
  var rows = [].map.call(l.querySelectorAll('.fleet-row'), function(row){
    var b = row.querySelector(':scope > b'), name = b ? b.textContent.replace(/\s+/g, ' ').trim() : '';
    var parts = [];
    if (b) parts.push({ k: 'name', rs: ink(b) });
    var w = row.querySelector(':scope > .fleet-word'); if (w) parts.push({ k: 'verdict', rs: ink(w) });
    [].forEach.call(row.querySelectorAll('.fleet-riverstuck, .fleet-pickerodd, .fleet-readeroff'), function(c){
      parts.push({ k: c.textContent.trim(), rs: ink(c) }); });
    var over = [];
    for (var i = 0; i < parts.length; i++) for (var j = i + 1; j < parts.length; j++)
      if (parts[i].rs.some(function(a){ return parts[j].rs.some(function(c){ return hit(a, c); }); }))
        over.push(parts[i].k + ' / ' + parts[j].k);
    var spill = parts.filter(function(p){ return p.rs.some(function(r){ return r.r > lr.right + 0.5; }); }).map(function(p){ return p.k; });
    return { name: name, words: name ? name.split(' ').length : 0, nameLines: b ? lines(ink(b)) : 0,
             chips: parts.filter(function(p){ return p.k !== 'name' && p.k !== 'verdict'; })
                         .map(function(p){ return { t: p.k, painted: p.rs.length > 0 }; }),
             over: over, spill: spill }; });
  return JSON.stringify({ rows: rows, w: lr.width }); } catch (e) { return JSON.stringify({ err: String(e) }); } })()"""

_CACHE = {}


def _render():
    if "r" in _CACHE:
        return _CACHE["r"]
    port = _free_port()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"], cwd=REPO,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = {}
    try:
        RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
        try:
            t = RC._Tab("about:blank")
            t.send("Page.enable")
            t.send("Runtime.enable")
            seed = SEED % json.dumps(_fleet())
            for (w, h) in WIDTHS:
                t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
                t.send("Page.navigate", url="http://127.0.0.1:%d/tv/control_ui.html" % port)
                for _ in range(120):
                    time.sleep(0.25)
                    try:
                        if t.ev("document.readyState==='complete' && !!window._fleetRefresh && !!document.getElementById('fleet-list')") is True:
                            break
                    except Exception:
                        pass
                else:
                    raise AssertionError("the fleet rail never loaded at %d - UNKNOWN, not passing" % w)
                t.ev(seed)
                for _ in range(80):
                    time.sleep(0.25)
                    try:
                        if (t.ev("document.querySelectorAll('#fleet-list .fleet-row').length") or 0) >= 5:
                            break
                    except Exception:
                        pass
                time.sleep(0.8)
                res["%dx%d" % (w, h)] = json.loads(t.ev(MEASURE))
            try:
                t.close()
            except Exception:
                pass
        finally:
            RC._chrome_down()
    finally:
        srv.kill()
        srv.wait(10)
    _CACHE["r"] = res
    return res


@unittest.skipUnless(os.path.exists(RC.CHROME or ""), "no Chrome on this machine - the rail was not rendered (declared skip 77)")
class TheFleetRowKeepsItsNameWhole(unittest.TestCase):

    def test_every_row_and_every_word_was_drawn(self):
        """PREMISE - PRINT THE DENOMINATOR: five rows at each width, and every exception word the stub carries painted."""
        for k, m in _render().items():
            self.assertNotIn("err", m, "%s: %r" % (k, m))
            self.assertEqual(len(m["rows"]), 5, "%s: %d rows drawn of 5" % (k, len(m["rows"])))
            words = sorted(c["t"] for r in m["rows"] for c in r["chips"])
            self.assertEqual(words, sorted(["river stuck"] * 3 + ["picker broken"] * 2 + ["Claude signed out"] * 2
                                           + ["Grok signed out"] * 2), "%s: the words drawn were %s" % (k, words))
            self.assertTrue(all(c["painted"] for r in m["rows"] for c in r["chips"]), "%s: a word has no ink" % k)

    def test_no_name_breaks_inside_a_word(self):
        bad = []
        for k, m in _render().items():
            for r in m.get("rows") or []:
                if r["nameLines"] > r["words"]:
                    bad.append("%s %r: %d lines for %d word(s)" % (k, r["name"], r["nameLines"], r["words"]))
        self.assertEqual(bad, [], "a PC's name is broken inside a word (the squeeze): " + "; ".join(bad))

    def test_no_two_words_of_a_row_print_over_each_other_or_past_the_rail(self):
        bad = []
        for k, m in _render().items():
            for r in m.get("rows") or []:
                if r["over"]:
                    bad.append("%s %r: %s" % (k, r["name"], ", ".join(r["over"])))
                if r["spill"]:
                    bad.append("%s %r runs past the rail: %s" % (k, r["name"], ", ".join(r["spill"])))
        self.assertEqual(bad, [], "; ".join(bad))


if __name__ == "__main__":
    unittest.main(verbosity=2)
