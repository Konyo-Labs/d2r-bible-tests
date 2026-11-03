# -*- coding: utf-8 -*-
"""v3849 - Esc leaves a shadow only when nothing is open.

The shadow bar carries a LEAVE SHADOW chip in the overlay-close colours, and a bigger
Their sessions entry. Escape closes the top overlay first (Their sessions on the parent,
or whatever __tvTopOverlay names) and asks the console to leave only when that stack is
empty. Cinema and a typed lookup still own the key. The two overlay-contract copies stay
identical, and .ssv-x is one both of them close.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from console_safe import enable
enable()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UI = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
BIBLE = open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
NODE = shutil.which("node")
BLOCK = re.compile(r"/\* OVERLAY-CONTRACT v3847.*?/\* /OVERLAY-CONTRACT \*/", re.S)
LEAVE_TEXT = ">\u2715 LEAVE SHADOW (Esc)</button>"
SESS_RULE = "#shadow-bar #shadow-sessions { font: var(--fw-bold) var(--fs-sm)/1.2 var(--mono); padding: 8px 16px; min-height: 44px; }"
LEAVE_RULE_OPEN = "#shadow-bar #shadow-leave { margin-left: 0; min-height: 44px; padding: 8px 16px;"
FRAME_GUARD = (
    "      if (top && top.x) {\n"
    "        ev.preventDefault();\n"
    "        try { top.x.click(); } catch (eK) {}\n"
    "        return;\n"
    "      }\n"
)
PARENT_SESS = (
    "    var sess = document.getElementById('shadow-sess-ov');\n"
    "    if (sess && !sess.hidden) {\n"
    "      if (typeof window._shadowSessionsClose === 'function') window._shadowSessionsClose();\n"
    "      return;\n"
    "    }\n"
)
PARENT_LEAVE = (
    "    if (!up || typeof window._shadowLeave !== 'function') return;\n"
    "    e.preventDefault();\n"
    "    window._shadowLeave();\n"
)
SSV = ".help-x,.ssv-x,.tvd-frame-lb-x,.ovx-made"


def _cut(src, start):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start[:60], src.count(start)))
    i = src.index(start)
    b = src.index("{", i)
    depth = 0
    j = b
    n = len(src)
    while j < n:
        c = src[j]
        if c in ("'", '"', "`"):
            q = c
            j += 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == q:
                    j += 1
                    break
                j += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = src.index(";", j)
                return src[i:end + 1]
        j += 1
    raise AssertionError("listener never closed")


FRAME_SRC = _cut(BIBLE, "    document.addEventListener('keydown', function (ev) {\n      if (ev.key !== 'Escape' || !host || host === window) return;")
KEY_SRC = _cut(UI, "  document.addEventListener('keydown', function(e){\n    if (e.key !== 'Escape' || e.defaultPrevented || e.isComposing) return;")
MSG_SRC = _cut(UI, "  window.addEventListener('message', function (ev) {\n    var f = document.getElementById('shadow-eng');")

HARNESS = r"""
var SRC = %s;
function boot(src){
  var posts = [], closed = 0, left = 0, clicks = 0, LISTEN = {};
  var host = { postMessage: function(m){ posts.push(m && m.type); } };
  function lookupBox(el){ return !!(el && el.lookup); }
  function _shadowSessionsClose(){ closed++; }
  var window = { location: { origin: 'http://127.0.0.1' },
    _shadowLeave: function(){ left++; },
    _shadowSessionsClose: function(){ closed++; } };
  var document = { fullscreenElement: null, body: null, _ids: {},
    addEventListener: function(t, f){ (LISTEN[t] = LISTEN[t] || []).push(f); },
    getElementById: function(id){ return document._ids[id] || null; } };
  window.addEventListener = function(t, f){ (LISTEN[t] = LISTEN[t] || []).push(f); };
  new Function('window','document','host','lookupBox','_shadowSessionsClose', src)(window, document, host, lookupBox, _shadowSessionsClose);
  function fire(type, ev){
    ev.preventDefault = function(){ ev.prevented = true; };
    var err = null;
    try { (LISTEN[type] || []).forEach(function(f){ f(ev); }); }
    catch (e) { err = String(e && e.message || e); }
    return { posts: posts.slice(), closed: closed, left: left, clicks: clicks, prevented: !!ev.prevented, err: err };
  }
  return { window: window, document: document, posts: posts, fire: fire,
    click: function(){ clicks++; }, reset: function(){ posts.length = 0; closed = 0; left = 0; clicks = 0; } };
}
function body(on){
  var cls = on || {};
  return { classList: { contains: function(c){ return !!cls[c]; } } };
}
var out = {};
var fr = boot(SRC.frame);
var x = { click: function(){ fr.click(); } };
fr.window.__tvTopOverlay = function(){ return { x: x }; };
out.frameOverlay = fr.fire('keydown', { key: 'Escape', target: {} });
fr.reset(); fr.window.__tvTopOverlay = function(){ return null; };
fr.document.body = body({});
out.frameEmpty = fr.fire('keydown', { key: 'Escape', target: {} });
fr.reset(); delete fr.window.__tvTopOverlay; fr.document.body = null;
out.frameNoFn = fr.fire('keydown', { key: 'Escape', target: {} });
fr.reset(); fr.document.body = body({ cinema: true }); fr.document.fullscreenElement = null;
out.frameCinema = fr.fire('keydown', { key: 'Escape', target: {} });
fr.reset(); fr.document.body = body({}); fr.document.fullscreenElement = {};
out.frameFull = fr.fire('keydown', { key: 'Escape', target: {} });
fr.reset(); fr.document.fullscreenElement = null;
var typed = { lookup: true, value: 'Nightwing', fired: [], dispatchEvent: function(e){ this.fired.push(e.type); } };
out.frameTyped = fr.fire('keydown', { key: 'Escape', target: typed });
out.frameTypedValue = typed.value;
out.frameTypedFired = typed.fired.slice();
fr.reset();
out.frameLookupEmpty = fr.fire('keydown', { key: 'Escape', target: { lookup: true, value: '' } });

var key = boot(SRC.key);
key.document._ids['shadow-sess-ov'] = { hidden: false };
key.document.body = body({ 'shadow-on': true });
out.keySess = key.fire('keydown', { key: 'Escape', target: {} });
key.reset(); key.document._ids['shadow-sess-ov'].hidden = true;
key.window.__tvTopOverlay = function(){ return { x: { click: function(){ key.click(); } } }; };
out.keyTop = key.fire('keydown', { key: 'Escape', target: {} });
key.reset(); key.window.__tvTopOverlay = function(){ return null; };
out.keyEmpty = key.fire('keydown', { key: 'Escape', target: {} });
key.reset(); key.document.body = body({});
out.keyNoShadow = key.fire('keydown', { key: 'Escape', target: {} });
key.reset(); key.document.body = body({ 'shadow-on': true });
out.keyInput = key.fire('keydown', { key: 'Escape', target: { closest: function(){ return this; } } });
key.reset(); key.document.body = body({ cinema: true, 'shadow-on': true });
out.keyCinema = key.fire('keydown', { key: 'Escape', target: {} });
key.reset(); delete key.window.__tvTopOverlay; key.document.body = body({ 'shadow-snap': true });
out.keyNoFn = key.fire('keydown', { key: 'Escape', target: {} });
key.reset(); key.document.body = null;
out.keyNoBody = key.fire('keydown', { key: 'Escape', target: {} });

var msg = boot(SRC.msg);
var eng = { contentWindow: {} };
msg.document._ids['shadow-eng'] = eng;
msg.document._ids['shadow-sess-ov'] = { hidden: false };
function packet(extra){
  var ev = { source: eng.contentWindow, origin: 'http://127.0.0.1', data: { type: 'tvd-shadow-leave' } };
  if (extra) for (var k in extra) ev[k] = extra[k];
  return ev;
}
out.msgSess = msg.fire('message', packet());
msg.reset(); msg.document._ids['shadow-sess-ov'].hidden = true;
msg.window.__tvTopOverlay = function(){ return { x: { click: function(){ msg.click(); } } }; };
out.msgTop = msg.fire('message', packet());
msg.reset(); msg.window.__tvTopOverlay = function(){ return null; };
out.msgEmpty = msg.fire('message', packet());
msg.reset();
out.msgForeign = msg.fire('message', packet({ origin: 'http://evil.example' }));
msg.reset();
out.msgOther = msg.fire('message', packet({ source: {} }));
msg.reset(); delete msg.window.__tvTopOverlay; delete msg.document._ids['shadow-sess-ov'];
out.msgNoFn = msg.fire('message', packet());
process.stdout.write(JSON.stringify(out));
"""


class EscLeavesAShadowOnlyWhenNothingIsOpen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        js = HARNESS % json.dumps({"frame": FRAME_SRC, "key": KEY_SRC, "msg": MSG_SRC})
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        if r.returncode != 0:
            raise AssertionError("the leave handlers did not run: %s" % (r.stderr[-900:],))
        cls.o = json.loads(r.stdout)

    def test_the_two_contracts_both_close_their_sessions(self):
        a, b = BLOCK.findall(UI), BLOCK.findall(BIBLE)
        self.assertEqual(len(a), 1)
        self.assertEqual(len(b), 1)
        self.assertEqual(a[0], b[0], "the overlay contract copies drifted")
        self.assertEqual(a[0].count(SSV), 1)
        self.assertEqual(BIBLE.count(SSV), 1)
        self.assertEqual(UI.count(SSV), 1)

    def test_leave_shadow_wears_the_overlay_close_chip(self):
        self.assertEqual(UI.count(LEAVE_TEXT), 1)
        self.assertIn('<div id="shadow-bar" hidden><span id="shadow-who">read only</span><button type="button" id="shadow-sessions"', UI)
        i = UI.index(LEAVE_RULE_OPEN)
        rule = UI[i:UI.index("}", i) + 1]
        self.assertIn("background: rgba(20,16,10,.92)", rule)
        self.assertIn("border: 1px solid rgba(255,190,110,.55)", rule)
        self.assertIn("min-height: 44px", rule)
        ox = re.search(r"/\* OVERLAY-X v3847.*?/\* /OVERLAY-X \*/", UI, re.S).group(0)
        self.assertNotIn("#shadow-leave", ox)

    def test_their_sessions_entry_is_bigger(self):
        self.assertEqual(UI.count(SESS_RULE), 1)

    def test_esc_in_the_frame_closes_an_overlay_before_it_leaves(self):
        o = self.o
        self.assertEqual(o["frameOverlay"], {"posts": [], "closed": 0, "left": 0, "clicks": 1, "prevented": True, "err": None})
        self.assertEqual(o["frameEmpty"]["posts"], ["tvd-shadow-leave"])
        self.assertIsNone(o["frameEmpty"]["err"])
        self.assertEqual(o["frameNoFn"]["posts"], ["tvd-shadow-leave"])
        self.assertIsNone(o["frameNoFn"]["err"])
        self.assertEqual(o["frameCinema"]["posts"], [])
        self.assertIsNone(o["frameCinema"]["err"])
        self.assertEqual(o["frameFull"]["posts"], [])
        self.assertEqual(o["frameTyped"]["posts"], [])
        self.assertEqual(o["frameTypedValue"], "")
        self.assertEqual(o["frameTypedFired"], ["input"])
        self.assertEqual(o["frameLookupEmpty"]["posts"], ["tvd-shadow-leave"])
        self.assertEqual(BIBLE.count(FRAME_GUARD), 1)

    def test_the_parent_closes_an_overlay_instead_of_leaving(self):
        o = self.o
        self.assertEqual(o["msgSess"]["closed"], 1)
        self.assertEqual(o["msgSess"]["left"], 0)
        self.assertIsNone(o["msgSess"]["err"])
        self.assertEqual(o["msgTop"]["clicks"], 1)
        self.assertEqual(o["msgTop"]["left"], 0)
        self.assertEqual(o["msgEmpty"]["left"], 1)
        self.assertEqual(o["msgForeign"]["left"], 0)
        self.assertEqual(o["msgOther"]["left"], 0)
        self.assertEqual(o["msgNoFn"]["left"], 1)
        self.assertIsNone(o["msgNoFn"]["err"])
        self.assertEqual(o["keySess"]["closed"], 1)
        self.assertEqual(o["keySess"]["left"], 0)
        self.assertEqual(o["keyTop"]["clicks"], 1)
        self.assertEqual(o["keyTop"]["left"], 0)
        self.assertEqual(o["keyEmpty"]["left"], 1)
        self.assertEqual(o["keyNoShadow"]["left"], 0)
        self.assertEqual(o["keyInput"]["left"], 0)
        self.assertEqual(o["keyCinema"]["left"], 0)
        self.assertEqual(o["keyNoFn"]["left"], 1)
        self.assertIsNone(o["keyNoFn"]["err"])
        self.assertIsNone(o["keyNoBody"]["err"])
        self.assertEqual(o["keyNoBody"]["left"], 0)
        self.assertEqual(UI.count(PARENT_SESS), 1)
        self.assertEqual(UI.count(PARENT_LEAVE), 1)


RED_PROOF = [
    {"why": "v3849 - LEAVE SHADOW drops back to a plain Leave",
     "file": "tv/control_ui.html",
     "find": ">\u2715 LEAVE SHADOW (Esc)</button>", "replace": ">Leave</button>", "matches": 1},
    {"why": "v3849 - Their sessions shrinks back to the bar's small chip",
     "file": "tv/control_ui.html",
     "find": "#shadow-bar #shadow-sessions { font: var(--fw-bold) var(--fs-sm)/1.2 var(--mono); padding: 8px 16px; min-height: 44px; }",
     "replace": "#shadow-bar #shadow-sessions { padding: 0; }", "matches": 1},
    {"why": "v3849 - Esc in the frame leaves while an overlay is open",
     "file": "bible.html",
     "find": "      if (top && top.x) {\n        ev.preventDefault();\n        try { top.x.click(); } catch (eK) {}\n        return;\n      }\n",
     "replace": "", "matches": 1},
    {"why": "v3849 - a leave from the frame exits even while Their sessions is open",
     "file": "tv/control_ui.html",
     "find": "    var sess = document.getElementById('shadow-sess-ov');\n    if (sess && !sess.hidden) {\n      if (typeof window._shadowSessionsClose === 'function') window._shadowSessionsClose();\n      return;\n    }\n",
     "replace": "", "matches": 1},
    {"why": "v3849 - Esc on the parent with nothing open no longer leaves the shadow",
     "file": "tv/control_ui.html",
     "find": "    if (!up || typeof window._shadowLeave !== 'function') return;\n    e.preventDefault();\n    window._shadowLeave();\n",
     "replace": "", "matches": 1},
    {"why": "v3849 - Their sessions close is not an overlay the contract closes",
     "file": "bible.html", "find": ".help-x,.ssv-x,.tvd-frame-lb-x,.ovx-made", "replace": ".help-x,.tvd-frame-lb-x,.ovx-made", "matches": 1},
    {"why": "v3849 - the console's contract copy no longer closes Their sessions",
     "file": "tv/control_ui.html", "find": ".help-x,.ssv-x,.tvd-frame-lb-x,.ovx-made", "replace": ".help-x,.tvd-frame-lb-x,.ovx-made", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
