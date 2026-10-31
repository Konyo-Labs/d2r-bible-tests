#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""REG-1685 - THE HEART OPENS ON ONE CLICK, NEVER STICKS, AND REFRESHES ITSELF.

His words, 2026-10-01: on the Windows ALT "it doesnt open", on his Mac "it opens after its double clicked like it says
couple seconds it will open but its stuck. needs a mechanism to refresh it". MEASURED that hour: /api/heart took 8.9 s
on his Mac and 27 s cold on the ALT (0 s inside its 45 s memo). The panel promised "a couple of seconds", its fetch had
NO timeout, and `if (_hrtBusy) return` swallowed every click while one census was in flight - closing the panel did
not reset it, so the next click did nothing.

THE SERVER HALF, driven through the real heart_state_now (the census itself is a stub, so this never walks his tree):
  1. a fresh memo answers as it is and starts nothing;
  2. a stale memo answers AT ONCE with its real age, stale + refreshing, and ONE background census starts - a second
     ask while it runs joins it; when it lands the next read is fresh;
  3. a census quick enough lands inside the same answer; ↻ (refresh=1) asks even when the memo is fresh;
  4. no census ever taken is `pending` while one runs, and ok:False with the reason when it failed - never a quiet
     panel waiting for nothing; the route sends ?fast=1 here.
THE PANEL HALF, the SHIPPED block executed in node against a stub overlay, a fake fetch and a virtual clock:
  5. a click while a census is on its way RE-SHOWS the panel (it was swallowed);
  6. a read that never answers ends at its bound, says so, and asks again by itself;
  7. a census still refreshing is shown with its age, the panel asks again until the fresh one lands and fills itself
     in, and then stops asking; closing it stops the asking;
  8. ↻ asks for a fresh census; no census yet says so and keeps asking; the placeholder no longer promises seconds.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402
_fx_tmp.contain()
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import control_app as ca  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
CENSUS = {"ok": True, "counts": {"FLOWING": 20, "WATCHED": 0, "DARK": 0, "UNKNOWN": 0}, "vessels": [], "locks": []}


class _Server(unittest.TestCase):

    def setUp(self):
        self._memo = dict(ca._HEART_MEMO)
        self._ref = dict(ca._HEART_REFRESH)
        self._hs = ca.heart_state
        ca._HEART_MEMO.update(t=0.0, done=0.0, v=None)
        ca._HEART_REFRESH.update(running=False, startedAt=None, lastTookMs=None, lastError=None, runs=0)
        self.calls = []
        self.take = 0.0
        self.fail = None

        def census(force=False):
            self.calls.append(force)
            t0 = time.time()
            time.sleep(self.take)
            if self.fail:
                return {"ok": False, "why": self.fail}
            out = dict(CENSUS)
            ca._heart_memo_store(t0, out)
            return out
        ca.heart_state = census
        self.addCleanup(self._restore)

    def _restore(self):
        self.settle()
        ca.heart_state = self._hs
        ca._HEART_MEMO.clear()
        ca._HEART_MEMO.update(self._memo)
        ca._HEART_REFRESH.clear()
        ca._HEART_REFRESH.update(self._ref)

    def settle(self, limit=10.0):
        end = time.time() + limit
        while ca._HEART_REFRESH.get("running") and time.time() < end:
            time.sleep(0.02)

    def memo(self, age_s):
        now = time.time()
        ca._HEART_MEMO.update(t=now - age_s, done=now - age_s, v=dict(CENSUS))


class TheServerAnswersAtOnce(_Server):

    def test_a_fresh_memo_answers_as_it_is(self):
        self.memo(5)
        r = ca.heart_state_now(wait_s=0)
        self.assertTrue(r.get("ok"))
        self.assertFalse(r.get("refreshing"))
        self.assertNotIn("stale", r)
        self.assertEqual(self.calls, [], "a fresh memo still walked the source")

    def test_a_stale_memo_answers_at_once_and_one_census_starts(self):
        self.memo(600)
        self.take = 0.5
        t0 = time.time()
        r = ca.heart_state_now(wait_s=0.05)
        self.assertLess(time.time() - t0, 0.4, "the click waited for the whole census")
        self.assertTrue(r.get("stale") and r.get("refreshing"), r)
        self.assertGreaterEqual(r.get("ageMs") or 0, 590000, "the stale census was not given its real age")
        r2 = ca.heart_state_now(wait_s=0.05)
        self.assertTrue(r2.get("refreshing"))
        self.settle()
        self.assertEqual(len(self.calls), 1, "a second ask started a second census: %r" % self.calls)
        r3 = ca.heart_state_now(wait_s=0)
        self.assertFalse(r3.get("refreshing"))
        self.assertNotIn("stale", r3, "the landed census still reads stale")
        self.assertLess(r3.get("ageMs") or 0, 5000)

    def test_a_quick_census_lands_inside_the_same_answer(self):
        self.memo(600)
        self.take = 0.05
        r = ca.heart_state_now(wait_s=2.0)
        self.assertFalse(r.get("refreshing"), r)
        self.assertNotIn("stale", r, "a census that landed in 50 ms was answered as the stale one")

    def test_refresh_asks_even_when_the_memo_is_fresh(self):
        self.memo(5)
        ca.heart_state_now(refresh=True, wait_s=1.0)
        self.settle()
        self.assertEqual(len(self.calls), 1, "↻ took no fresh census")

    def test_no_census_yet_is_pending_while_one_runs(self):
        self.take = 0.5
        r = ca.heart_state_now(wait_s=0.05)
        self.assertTrue(r.get("pending"), r)
        self.assertIsNone(r.get("ok"), "a census nobody has taken yet read as an answer")
        self.assertTrue(r.get("refreshing"))

    def test_a_failed_census_says_why_and_never_pends_for_nothing(self):
        self.fail = "the census could not be taken (boom)"
        r = ca.heart_state_now(wait_s=2.0)
        self.assertIs(r.get("ok"), False, r)
        self.assertFalse(r.get("pending"), "a failed census left the panel pending for a census nobody is taking")
        self.assertIn("boom", r.get("why") or "")

    def test_the_route_sends_fast_reads_here(self):
        src = io.open(os.path.join(HERE, "control_app.py"), encoding="utf-8").read()
        code = "\n".join(l.split("#", 1)[0] for l in src.split("\n"))
        self.assertEqual(code.count('self._json(200, heart_state_now(refresh=("refresh=1" in (self.path or ""))))'),
                         1, "/api/heart?fast=1 does not reach heart_state_now")


# ══ THE PANEL ══════════════════════════════════════════════════════════════════════════════════════════════════════

def _node():
    return shutil.which("node") or shutil.which("nodejs")


def _block():
    """The SHIPPED REG-1685 block: its helpers and _heartOpen, bounded by _heartClose - never a byte window."""
    src = io.open(UI, encoding="utf-8", errors="replace").read()
    i = src.find("  var _hrtPollT = null, _hrtPolls = 0, _hrtTookMs = null, _hrtForceNext = false;")
    j = src.find("  function _heartClose(){", i)
    assert i > 0 and j > i, "the REG-1685 block or _heartClose is gone from control_ui.html"
    return src[i:j]


HARNESS = r"""
var window = {}, PAINTS = [], CALLS = [], TIMERS = [], NOW = 0;
function setTimeout(fn, ms){ var t = {fn: fn, at: NOW + (ms || 0), id: TIMERS.length + 1}; TIMERS.push(t); return t.id; }
function clearTimeout(id){ TIMERS = TIMERS.filter(function(t){ return t.id !== id; }); }
/* REG-2073 - the census age now ticks on a setInterval while the panel is open; the panel here never closes, and node's
   real interval kept the process alive until the 60 s timeout. Recorded on the harness clock, never fired - the tick has
   its own law (test_the_census_age_ticks_from_its_stamp). */
var INTERVALS = [];
function setInterval(fn, ms){ INTERVALS.push({fn: fn, ms: ms}); return 100000 + INTERVALS.length; }
function clearInterval(id){}
function fetch(url){ return new Promise(function(res, rej){ CALLS.push({url: url, res: res, rej: rej}); }); }
function answer(d){ var c = CALLS[CALLS.length - 1]; c.res({ json: function(){ return Promise.resolve(d); } }); }
function mk(id){ return { id: id, children: [], textContent: '', className: '', attrs: {},
  setAttribute: function(k, v){ this.attrs[k] = v; }, getAttribute: function(k){ return this.attrs[k]; } }; }
function Head(){ var h = mk('head'); h.querySelector = function(sel){
    for (var k = 0; k < this.children.length; k++) if ('#' + this.children[k].id === sel) return this.children[k];
    return sel === '#hrt-close' ? { id: 'hrt-close' } : null; };
  h.appendChild = function(c){ this.children.push(c); return c; };
  h.insertBefore = function(c){ this.children.push(c); return c; }; return h; }
var OV = { hidden: true, attrs: {}, _html: '', head: null, body: null,
  setAttribute: function(k, v){ this.attrs[k] = v; },
  get innerHTML(){ return this._html; },
  set innerHTML(v){ this._html = v; this.head = /hrt-head/.test(v) ? Head() : null;
                    this.body = /fx-body/.test(v) ? Head() : null; },
  querySelector: function(sel){
    if (sel === '.hrt-h') return /class="hrt-h/.test(this._html) ? {} : null;
    if (sel === '.hrt-head') return this.head;
    if (sel === '.fx-body') return this.body;
    if (sel.charAt(0) === '#') {
      var hit = (this.head && this.head.querySelector(sel));
      if (hit && hit.id === sel.slice(1)) return hit;
      hit = this.body && this.body.querySelector(sel);
      return (hit && hit.id === sel.slice(1)) ? hit : (sel === '#hrt-close' ? { id: 'hrt-close' } : null); }
    return null; } };
var document = { getElementById: function(id){ return id === 'heart-ov' ? OV : null; },
                 createElement: function(){ return mk(''); } };
var _hrtBusy = false;
function _hrtBuild(d){ return '<div class="fxr-win hrt-win"><div class="fx-head hrt-head">HEAD</div><div class="fx-body">'
  + (d && d.ok ? '<div class="hrt-h">VESSELS</div>' : '<div class="hrt-note">' + ((d && d.why) || 'no census') + '</div>')
  + '</div></div>'; }
function _hrtFanFit(){ return { ok: true }; }
function _heartChipPaint(d){ PAINTS.push(d === null ? null : 'census'); }
function _hrtEsc(s){ return String(s); }
function flush(){ return new Promise(function(r){ setImmediate(r); }).then(function(){
  return new Promise(function(r){ setImmediate(r); }); }); }
async function advance(ms){ var end = NOW + ms;
  while (true) { TIMERS.sort(function(a, b){ return a.at - b.at; });
    var t = TIMERS[0]; if (!t || t.at > end) break;
    TIMERS.shift(); NOW = t.at; t.fn(); await flush(); }
  NOW = end; await flush(); }
function age(){ var a = OV.querySelector('#hrt-age'); return a ? a.textContent : null; }
function refreshBtn(){ return !!(OV.head && OV.head.querySelector('#hrt-refresh')); }
function state(){ return { hidden: OV.hidden, html: OV._html, calls: CALLS.map(function(c){ return c.url; }),
  age: age(), refresh: refreshBtn(), busy: _hrtBusy, paints: PAINTS, timers: TIMERS.length }; }
"""

STALE = {"ok": True, "counts": {"FLOWING": 20}, "ageMs": 600000, "stale": True, "refreshing": True,
         "refresh": {"running": True, "lastTookMs": 27000}}
FRESH = {"ok": True, "counts": {"FLOWING": 20}, "ageMs": 1000, "refreshing": False,
         "refresh": {"running": False, "lastTookMs": 27000}}
PENDING = {"ok": None, "pending": True, "refreshing": True, "ageMs": None, "refresh": {"running": True}}


class ThePanelNeverSticks(unittest.TestCase):

    def setUp(self):
        if not _node():
            self.skipTest("no node on this machine - the shipped panel cannot be EXECUTED, and reading it is not "
                          "running it")

    def run_js(self, scenario):
        prog = HARNESS + _block() + "\n(async function(){\n" + scenario + "\n})().catch(function(e){ " \
               "console.log(JSON.stringify({threw: String(e && e.stack || e)})); });\n"
        p = subprocess.run([_node(), "-"], input=prog, capture_output=True, text=True, timeout=60,
                           encoding="utf-8")
        if p.returncode != 0:
            raise AssertionError("node could not run the shipped panel: %s" % (p.stderr or "")[:400])
        out = [json.loads(l) for l in p.stdout.strip().split("\n") if l.startswith("{")]
        for o in out:
            self.assertNotIn("threw", o, o.get("threw"))
        return out

    def test_a_click_while_a_census_is_on_its_way_reshows_the_panel(self):
        a, b = self.run_js("""
            _heartOpen(); await flush();
            OV.hidden = true;                       /* he closes it while the census is on its way */
            console.log(JSON.stringify(state()));
            _heartOpen(); await flush();            /* and clicks the chip again */
            console.log(JSON.stringify(state()));""")
        self.assertTrue(a["busy"], "PREMISE: the first census is not in flight")
        self.assertFalse(b["hidden"], "the second click was swallowed - the panel stayed shut while a census ran")
        self.assertEqual(len(b["calls"]), 1, "a re-show started a second read")

    def test_a_read_that_never_answers_ends_says_so_and_asks_again(self):
        a, b = self.run_js("""
            _heartOpen(); await flush();
            await advance(26000);                   /* the console never answers */
            console.log(JSON.stringify(state()));
            await advance(5100);
            console.log(JSON.stringify(state()));""")
        self.assertFalse(a["busy"], "a read that never answered held the panel busy for ever")
        self.assertIn("no answer in 25 s", a["html"], "the panel did not say the console gave no answer")
        self.assertTrue(a["refresh"], "the failure offers no ↻")
        self.assertIn(None, a["paints"], "the chip kept a clean face beside a panel that got no answer")
        self.assertEqual(len(b["calls"]), 2, "the panel never asked again after a read with no answer")

    def test_a_refreshing_census_is_shown_then_fills_itself_in_then_stops(self):
        outs = self.run_js("""
            _heartOpen(); await flush();
            answer(%s); await flush();
            console.log(JSON.stringify(state()));
            await advance(3100);
            console.log(JSON.stringify(state()));
            answer(%s); await flush();
            await advance(10000);
            console.log(JSON.stringify(state()));""" % (json.dumps(STALE), json.dumps(FRESH)))
        a, b, c = outs
        self.assertIn("VESSELS", a["html"], "a census on its way to refreshing was not shown at once")
        self.assertIn("10 min ago", a["age"] or "", "the stale census does not say how old it is: %r" % a["age"])
        self.assertIn("being taken", a["age"] or "")
        self.assertIn("27 s", a["age"] or "", "the panel does not say how long the last census took")
        self.assertEqual(len(b["calls"]), 2, "the panel never asked again while a fresh census was being taken")
        self.assertTrue(b["calls"][1].startswith("/api/heart?fast=1"), b["calls"])
        self.assertIn("1 s ago", c["age"] or "", "the fresh census never filled the panel in: %r" % c["age"])
        self.assertNotIn("being taken", c["age"] or "")
        self.assertEqual(len(c["calls"]), 2, "the panel kept asking after the fresh census landed")

    def test_closing_the_panel_stops_the_asking(self):
        (a,) = self.run_js("""
            _heartOpen(); await flush();
            answer(%s); await flush();
            OV.hidden = true;
            await advance(30000);
            console.log(JSON.stringify(state()));""" % json.dumps(STALE))
        self.assertEqual(len(a["calls"]), 1, "a closed panel went on asking the console: %r" % a["calls"])

    def test_refresh_asks_for_a_fresh_census(self):
        (a,) = self.run_js("""
            _heartOpen('force'); await flush();
            console.log(JSON.stringify(state()));""")
        self.assertEqual(a["calls"], ["/api/heart?fast=1&refresh=1"], a["calls"])

    def test_no_census_yet_says_so_and_keeps_asking(self):
        (a,) = self.run_js("""
            _heartOpen(); await flush();
            answer(%s); await flush();
            await advance(3100);
            console.log(JSON.stringify(state()));""" % json.dumps(PENDING))
        self.assertIn("no census is showing", a["age"] or "", a["age"])
        self.assertEqual(len(a["calls"]), 2, "a pending census was not asked for again")

    def test_the_placeholder_no_longer_promises_seconds(self):
        (a,) = self.run_js("""
            _heartOpen(); await flush();
            console.log(JSON.stringify(state()));""")
        self.assertIn("taking the census", a["html"])
        self.assertNotIn("a couple of seconds", a["html"], "the placeholder still promises seconds it cannot keep")
        self.assertIn("fills itself in", a["html"])

    def test_the_refresh_button_is_wired_to_a_forced_census(self):
        src = io.open(UI, encoding="utf-8").read()
        self.assertEqual(src.count("ev.target.closest('#hrt-refresh')) { _hrtPolls = 0; _heartOpen('force'); return; }"),
                         1, "↻ is drawn but nothing takes a fresh census when he presses it")


RED_PROOF = [
    {"why": "REG-1685 - a click while a census is on its way is swallowed again",
     "file": "control_ui.html",
     "find": "      else if (again !== 'again') ov.hidden = false;\n",
     "replace": "      else if (false) ov.hidden = false;\n",
     "matches": 1},
    {"why": "REG-1685 - the read has no bound: a console that never answers holds the panel for ever",
     "file": "control_ui.html",
     "find": "        if (!done) { done = true; rej(new Error('the console gave no answer in ' + Math.round(ms / 1000) + ' s')); }\n",
     "replace": "        if (false) { done = true; }\n",
     "matches": 1},
    {"why": "REG-1685 - the panel never asks again while a fresh census is being taken",
     "file": "control_ui.html",
     "find": "      if (d && d.refreshing && _hrtPolls++ < _HRT_POLL_MAX) _hrtSchedule(_HRT_POLL_MS);\n",
     "replace": "      if (false) _hrtSchedule(_HRT_POLL_MS);\n",
     "matches": 1},
    {"why": "REG-1685 - a closed panel goes on asking the console",
     "file": "control_ui.html",
     "find": "    if (again === 'again' && ov.hidden) return;          /* closed: the panel stops asking */\n",
     "replace": "    /* closed: the panel stops asking */\n",
     "matches": 1},
    {"why": "REG-1685 - the panel reads the slow census again instead of the fast read",
     "file": "control_ui.html",
     "find": "    _hrtFetch('/api/heart?fast=1' + (again === 'force' ? '&refresh=1' : ''), _HRT_FETCH_MS).then(function(d){\n",
     "replace": "    _hrtFetch('/api/heart' + (again === 'force' ? '?force=1' : ''), _HRT_FETCH_MS).then(function(d){\n",
     "matches": 1},
    {"why": "REG-1685 - the server waits for the whole census before answering a click",
     "file": "control_app.py",
     "find": "        while _HEART_REFRESH[\"running\"] and _t.time() < end:\n",
     "replace": "        while _HEART_REFRESH[\"running\"]:\n",
     "matches": 1},
    {"why": "REG-1685 - a second ask while a census runs starts a second census",
     "file": "control_app.py",
     "find": "            if age < _HEART_REFRESH_STUCK_S or gave_up:\n",
     "replace": "            if False:\n",
     "matches": 1},
    {"why": "REG-1685 - a stale census is shown without saying it is stale",
     "file": "control_app.py",
     "find": "        if out is not None:\n            out[\"stale\"] = True\n",
     "replace": "        if out is not None:\n            pass\n",
     "matches": 1},
    {"why": "REG-1685 - a failed census leaves the panel pending for nothing",
     "file": "control_app.py",
     "find": "        elif st.get(\"running\"):\n            out = {\"ok\": None, \"pending\": True,",
     "replace": "        elif True:\n            out = {\"ok\": None, \"pending\": True,",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
