# -*- coding: utf-8 -*-
"""REG-3202 (GrokBot on v3864, his Mac console and a guest console: "Full bible ->" is a no-op) - THE FULL BIBLE DOOR
OPENS THE FULL BIBLE.

His ask (v3286): "the button within the console that routes us to the full bible page". MEASURED in source on v3864:
the door was `href="#"` with `onclick="if(window._shellOpen){window._shellOpen('session');}return false;"`. That
promoted the engine pane on the board's SESSIONS room - the Task Force the Sessions hub already shows, under a header
that already lit Sessions - and the pane hides the board's own tab row (bible.html v935.6:
`body.app-ctx.engine-driven .tabs{display:none !important}`), so no other room of the bible could be reached. In a
shadow it promoted #tvd-eng, which `body.shadow-on #tvd-eng` hides (visibility:hidden !important), and left
shadow-hub on: nothing on screen moved.

THE LAW, on the SHIPPED functions (openFullBible, shellOpen, _shellRoute, _shellRestoreConsole and the two full-mode
helpers, cut from control_ui.html and run in node over a fake page and a fake board):
  1. the anchor's href is the full page itself, and its click returns false only when the door opened the pane;
  2. the door opens the pane in FULL mode: this body carries data-full-bible="1", the board's body carries bible-full,
     and the board is on its Sessions room;
  3. any other route (a header tab's shellOpen) and every way home (_shellRestoreConsole) leave full mode, on both
     this body and the board's;
  4. in a shadow the door drops shadow-hub and THEIR board (#shadow-eng) gets full mode, on Characters - the room a
     shadow opens on (their board's Sessions room is the console's hub, which the header tab and the board refuse);
  5. bible.html shows its whole rail - every tab, the data clusters too - only under bible-full, after the engine
     rule that hides it.
A missing node raises; this law does not skip. RED_PROOF below.
"""
import io
import json
import os
import re
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
from cb_node_harness import NODE  # noqa: E402

UI = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
BIBLE = io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()

ANCHOR = ('<a class="hub-bible" id="hub-bible" href="/board?app=1#session" title="open the full bible — every room, '
          'deep session data, ledgers, tools" onclick="return !(window._openFullBible &amp;&amp; '
          'window._openFullBible());">')
FNS = ["  function _fullBibleMark(on){", "  function _fullBibleRail(w){", "  function openFullBible(){",
       "  function shellOpen(tab){", "  function _shellRoute(tab){", "  function _shellRestoreConsole(){"]
LINES = ["  var _fullBibleNext = false;", "  window._openFullBible = openFullBible;"]
RAIL_HIDE = "body.app-ctx.engine-driven .tabs{display:none !important}"
RAIL_SHOW = "body.app-ctx.engine-driven.bible-full .tabs{display:flex !important;flex-wrap:wrap}"
TAB_SHOW = "body.app-ctx.bible-full .tabs .tab{display:inline-flex}"
DATA_SHOW = "body.app-ctx.bible-full .tabs-data{display:flex}"


def _strip_js_comments(src):
    """block comments out, so a rule quoted in a comment is never counted as the rule"""
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def _cut(src, sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times" % (sig, src.count(sig)))
    i = src.index(sig)
    b = src.index("{", i)
    depth = 0
    for j in range(b, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
    raise AssertionError("%r never closed" % sig)


def _line(src, start):
    if src.count(start) != 1:
        raise AssertionError("%r occurs %d times" % (start, src.count(start)))
    i = src.index(start)
    return src[i:src.index("\n", i)]


HARNESS = r"""
function CL(init){ var s = {}; (init || []).forEach(function(c){ s[c] = 1; });
  return { add: function(){ for (var i = 0; i < arguments.length; i++) s[arguments[i]] = 1; },
           remove: function(){ for (var i = 0; i < arguments.length; i++) delete s[arguments[i]]; },
           contains: function(c){ return !!s[c]; },
           toggle: function(c, on){ if (on === undefined) on = !s[c]; if (on) s[c] = 1; else delete s[c]; return on; },
           list: function(){ return Object.keys(s).sort(); } }; }
function Board(){
  var self = this;
  this.active = 'session';
  this.document = { body: { classList: CL([]) },
                    querySelector: function(q){ return q === '.tab.active' ? { getAttribute: function(){ return self.active; } } : null; } };
  this.history = { replaceState: function(){} };
  this.switchTab = function(t){ self.active = t; };
}
var ATTR = {};
var body = { classList: CL(CFG.bodyClasses), dataset: {},
             setAttribute: function(k, v){ ATTR[k] = String(v); }, removeAttribute: function(k){ delete ATTR[k]; },
             getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(ATTR, k) ? ATTR[k] : null; } };
var ENG = { id: 'tvd-eng', style: {}, contentWindow: new Board() };
var SHADOW = { id: 'shadow-eng', style: {}, contentWindow: new Board() };
var document = {
  body: body, visibilityState: 'visible',
  getElementById: function(id){ return id === 'tvd-eng' ? ENG : id === 'shadow-eng' ? SHADOW : null; },
  querySelector: function(){ return null; },
  querySelectorAll: function(){ return []; }
};
var window = {};
var CALLS = [];
var _shellTab = 'tvd', _shellRouteTimer = null;
function setInterval(){ return 1; }
function clearInterval(){}
function _glide(u){ CALLS.push('glide ' + u); }
function _shellSizePane(){ CALLS.push('size'); }
function _shellLight(t){ CALLS.push('light ' + t); }
function _shellVeil(){}
function _shellOpeningEnd(){}
function toast(){}
function fetch(){ CALLS.push('fetch'); return { then: function(){} }; }
""" + "\n%s\n" + r"""
function snap(tag){
  return { tag: tag, full: body.getAttribute('data-full-bible'), shell: body.classList.contains('shell-open'),
           hub: body.classList.contains('shadow-hub'),
           engFull: ENG.contentWindow.document.body.classList.contains('bible-full'),
           shadowFull: SHADOW.contentWindow.document.body.classList.contains('bible-full'),
           engTab: ENG.contentWindow.active, shadowTab: SHADOW.contentWindow.active };
}
var OUT = [];
var ret = openFullBible();
OUT.push(snap('door')); OUT[0].ret = ret;
shellOpen('forge');
OUT.push(snap('header tab'));
openFullBible();
OUT.push(snap('door again'));
_shellRestoreConsole();
OUT.push(snap('home'));
process.stdout.write(JSON.stringify({ out: OUT, calls: CALLS, exported: typeof window._openFullBible }));
"""


def _drive(body_classes):
    if NODE is None:
        raise AssertionError("node is not installed on this PC - this law runs the shipped door in node and does not skip")
    code = "\n".join([_line(UI, x) for x in LINES] + [_cut(UI, x) for x in FNS])
    prog = "var CFG = " + json.dumps({"bodyClasses": body_classes}) + ";\n" + (HARNESS % code)
    p = subprocess.run([NODE, "-"], input=prog.encode("utf-8"), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=60)
    if p.returncode != 0:
        raise AssertionError("node failed: %s" % p.stderr.decode("utf-8", "replace")[-1500:])
    return json.loads(p.stdout.decode("utf-8"))


class TheFullBibleDoorOpensTheFullBible(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.own = _drive([])
        cls.shadow = _drive(["shadow-on", "shadow-snap", "shadow-hub"])

    def test_the_anchor_goes_somewhere_real(self):
        self.assertEqual(UI.count(ANCHOR), 1, "the Full Bible anchor is not the one that opens the full bible "
                                              "(a real href, a click that only cancels when the door opened)")
        self.assertEqual(UI.count('id="hub-bible"'), 1)
        self.assertNotIn('id="hub-bible" href="#"', UI, "the door went back to href=\"#\" - a link to nowhere")

    def test_the_door_opens_the_pane_in_full_mode(self):
        d = self.own["out"][0]
        self.assertTrue(d["ret"], "the door said it opened nothing: %r" % d)
        self.assertEqual(d["full"], "1", "this body is not marked full: %r" % d)
        self.assertTrue(d["shell"], "the pane was not promoted: %r" % d)
        self.assertTrue(d["engFull"], "the board never got bible-full, so its own rail stays hidden: %r" % d)
        self.assertEqual(d["engTab"], "session", d)
        self.assertEqual(self.own["exported"], "function", "window._openFullBible is not exported for the anchor")

    def test_any_other_route_leaves_full_mode(self):
        h = self.own["out"][1]
        self.assertIsNone(h["full"], "a header tab kept the full bible: %r" % h)
        self.assertFalse(h["engFull"], "the board kept its rail after a header tab: %r" % h)
        self.assertEqual(h["engTab"], "forge", h)
        again = self.own["out"][2]
        self.assertEqual(again["full"], "1", again)
        self.assertTrue(again["engFull"], again)
        home = self.own["out"][3]
        self.assertIsNone(home["full"], "going home kept the full bible mark: %r" % home)
        self.assertFalse(home["engFull"], "going home left the board's rail on: %r" % home)

    def test_in_a_shadow_it_is_their_board(self):
        d = self.shadow["out"][0]
        self.assertFalse(d["hub"], "the door left shadow-hub on, which keeps their frame hidden: %r" % d)
        self.assertTrue(d["shadowFull"], "their board did not get bible-full: %r" % d)
        self.assertEqual(d["shadowTab"], "chars", "a shadow's full bible opens on their Characters room, never their "
                                                  "board's Sessions (the console's hub): %r" % d)
        self.assertTrue(d["shell"], d)

    def test_the_board_shows_its_whole_rail_only_in_full_mode(self):
        css = _strip_js_comments(BIBLE)
        for rule in (RAIL_HIDE, RAIL_SHOW, TAB_SHOW, DATA_SHOW):
            self.assertEqual(css.count(rule), 1, "bible.html must carry %r exactly once" % rule)
        self.assertGreater(css.index(RAIL_SHOW), css.index(RAIL_HIDE),
                           "the full-mode rail must come after the engine rule that hides it")
        self.assertIn("display:flex !important", RAIL_SHOW)


class TheProofsNameOnePlace(unittest.TestCase):

    def test_each_find_matches_once(self):
        for proof in RED_PROOF:
            src = BIBLE if proof["file"] == "bible.html" else UI
            self.assertEqual(src.count(proof["find"]), proof["matches"], proof["why"])


RED_PROOF = [
    {"why": "REG-3202 - the door is a link to nowhere again",
     "file": "tv/control_ui.html",
     "find": 'id="hub-bible" href="/board?app=1#session"',
     "replace": 'id="hub-bible" href="#"',
     "matches": 1},
    {"why": "REG-3202 - the door's open is not marked full, so the board's rail stays hidden",
     "file": "tv/control_ui.html",
     "find": "    if (typeof _fullBibleMark === 'function') _fullBibleMark(_full);\n",
     "replace": "    if (typeof _fullBibleMark === 'function') _fullBibleMark(false);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3202 - the route never tells the board it is the full bible",
     "file": "tv/control_ui.html",
     "find": "      if (typeof _fullBibleRail === 'function') _fullBibleRail(w);   /* REG-3202",
     "replace": "      void 0;   /* REG-3202",
     "matches": 1, "needs": "node"},
    {"why": "REG-3202 - in a shadow the door leaves shadow-hub on and their board stays hidden",
     "file": "tv/control_ui.html",
     "find": "      if (shadow) b.classList.remove('shadow-hub');\n",
     "replace": "      if (shadow) void 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3202 - a shadow's door lands on their board's Sessions room, which is this console's hub",
     "file": "tv/control_ui.html",
     "find": "    try { shellOpen(shadow ? 'chars' : 'session'); }\n",
     "replace": "    try { shellOpen('session'); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3202 - going home keeps the full bible mark",
     "file": "tv/control_ui.html",
     "find": "    if (typeof _fullBibleMark === 'function') _fullBibleMark(false);   /* REG-3202 - leaving the pane leaves the full bible */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3202 - the board never shows its rail in full mode",
     "file": "bible.html",
     "find": "body.app-ctx.engine-driven.bible-full .tabs{display:flex !important;flex-wrap:wrap}",
     "replace": "body.app-ctx.engine-driven.bible-full .tabs{display:none !important;flex-wrap:wrap}",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
