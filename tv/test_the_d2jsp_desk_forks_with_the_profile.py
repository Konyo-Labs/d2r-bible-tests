# -*- coding: utf-8 -*-
"""#114 (REG-2502) - THE D2JSP DESK FORKS WITH THE PROFILE.

None of the six desk stores (d2r_d2jsp_topic, _fg, _sold, _hide, _gear, _mods) was in window._LP_FORKED, so main
(board 268) and ladder (board 271) shared them: post on main, then on ladder (which overwrote the saved topic),
then on main again, and a second 268 topic went up while the first was live; a price typed for 268 filled a 271
draft. They are forked now, as their own block at the head of the Set.

NO MIGRATION OF FILINGS BETWEEN PROFILES: on the owner's board main keeps the bare values it holds and ladder starts
with an empty list, because ladder is a separate item pool. A GUEST world (an unclaimed browser) wrote these keys bare
too and now reads them under its install prefix, so its main copies each bare value into its own key while that key
is empty - never the owner, never over a value already there.

THE ONE THING THAT NAMES ITS BOARD - THE LIVE LADDER TOPIC. Bare, both profiles shared one saved topic, which held
whichever board posted last. If ladder posted last, the bare key holds a topic on board 271 that is live on d2jsp.
Stranded under the fork, the next ladder "Post the list" sent no topic and the console opened a SECOND 271 topic
(the review's probe: the payload went out as {subject, body, forum: 271} with no topic). A ladder - owner L, guest
IL - copies a bare 271 topic into its own key while that key is empty; a 271 topic never lands in a main key and a
268 topic never on ladder. This law drives the real "Post the list" click and reads the topic the console is sent.

Runs the REAL router and the REAL room in node: the fork sets and window.LSR are sliced from bible.html by anchor
(as test_export_scopes_to_one_world does), `LS` is the router exactly as `const LS = window.LSR` makes it on the
page, and the room's own click and input handlers write through its own store(). The raw store is then read key
by key: a ladder write that lands bare, or a main write that lands prefixed, goes red.
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
KEYS = ("d2r_d2jsp_topic", "d2r_d2jsp_fg", "d2r_d2jsp_sold", "d2r_d2jsp_hide", "d2r_d2jsp_gear", "d2r_d2jsp_mods",
        "d2r_d2jsp_log")   # REG-2872 the post log forks with the desk
TOPIC = "https://forums.d2jsp.org/topic.php?t=1&f=268"


def _read():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _slice(src, start, end, inclusive=True):
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + (len(end) if inclusive else 0)]


def _node(prog):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


WORLD = r"""
var RAW = %(raw)s;
var RAWAPI = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
               setItem: function(k, v){ RAW[k] = String(v); }, removeItem: function(k){ delete RAW[k]; } };
var window = { localStorage: RAWAPI, addEventListener: function(){}, D2R_PROFILE: %(profile)s,
               _D2R_OWNER: %(owner)s, _D2R_PFX: %(pfx)s, _D2R_LPFX: %(lpfx)s };
var localStorage = RAWAPI;
%(lp)s
%(wp)s
%(lsr)s
var LS = window.LSR;   // the page's own alias: const LS = window.LSR
var SAID = [];
var LISTEN = { click: [], input: [], keydown: [] };
function Node(id){ this.id = id; this.attrs = {}; this.hidden = true; this._html = ''; this._t = ''; this.title = ''; }
Node.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
Node.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
Node.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
Node.prototype.querySelector = function(){ return { focus: function(){} }; };
Node.prototype.querySelectorAll = function(){ return []; };
Node.prototype.appendChild = function(){};
Object.defineProperty(Node.prototype, 'innerHTML', { get: function(){ return this._html; }, set: function(v){ this._html = String(v); } });
Object.defineProperty(Node.prototype, 'textContent', { get: function(){ return this._t; }, set: function(v){ this._t = String(v); if (this.id === 'd2jsp-status' && v) SAID.push(String(v)); } });
var NODES = {};
var VIEW = { textContent: '' }, SUBJECT = { textContent: '' };
['d2jsp-list', 'd2jsp-status', 'd2jsp-lamp', 'd2jsp-draft-host', 'd2jsp-board'].forEach(function(id){ NODES[id] = new Node(id); });
var document = {
  documentElement: { classList: { contains: function(){ return false; } } },
  getElementById: function(id){ return NODES[id] || null; },
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
var MULE = JSON.stringify({ 'Grief': 'm1', 'Shako': 'm1' });
var _route = window.LSR.getItem;
window.LSR.getItem = function(k){ return k === 'd2r_muleAssign' ? MULE : _route(k); };
var location = { hostname: '127.0.0.1' };
var SENT = [];
function fetch(url, opts){
  if (String(url) === '/api/d2jsp_send') {
    SENT.push(JSON.parse(opts.body));
    var answer = (typeof SEND_ANSWER !== 'undefined' && SEND_ANSWER) ? SEND_ANSWER : { ok: false, reason: 'maybe-sent', board: 271, at: 'x' };
    return Promise.resolve({ status: 200, json: function(){ return Promise.resolve(answer); } });
  }
  return Promise.resolve({ json: function(){ return Promise.resolve({ fg: null, reason: 'no prices', n: 0 }); } });
}
function flush(){ return new Promise(function(r){ setTimeout(r, 0); }); }
"""

SCENARIO = r"""
(async function(){
  var out = { keys: {} };
  KEYS.forEach(function(k){ out.keys[k] = window.LSR.key(k); });
  out.afterLoad = JSON.parse(JSON.stringify(RAW));
  window._d2jspShow();
  for (var i = 0; i < 4; i++) await flush();
  out.card = NODES['d2jsp-list']._html;
  window._d2jspShow();
  for (var j = 0; j < 4; j++) await flush();
  var rm = { getAttribute: function(k){ return k === 'data-d2jsp-remove' ? 'Shako' : null; } };
  rm.closest = function(sel){ return (sel === '#tab-d2jsp' || sel === '[data-d2jsp-remove]') ? rm : null; };
  LISTEN.click[0]({ target: rm, preventDefault: function(){} });
  LISTEN.input[0]({ target: { id: '', value: '77', getAttribute: function(k){ return k === 'data-d2jsp-fg' ? 'Grief' : null; } } });
  out.raw = RAW;
  out.said = SAID;
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""


@unittest.skipUnless(NODE, "node is required to run the router and the room")
class TheD2jspDeskForksWithTheProfile(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        cls.lp = _slice(cls.src, "window._LP_FORKED = new Set(", "window._WP_FORKED", inclusive=False)
        cls.wp = _slice(cls.src, "window._WP_FORKED = new Set(", "\ntry {", inclusive=False)
        cls.lsr = _slice(cls.src, "window.LSR = (function(){", "\n})();")
        pane = cls.src[cls.src.index('id="tab-d2jsp"'):cls.src.index('id="tab-vault"')]
        cls.script = pane.split("<script>", 1)[1].split("</script>", 1)[0]

    def _world(self, profile, owner, raw):
        pfx = "" if owner else "I·abcd1234·"
        lpfx = "L·" if owner else "IL·abcd1234·"
        prog = WORLD % {"raw": json.dumps(raw), "profile": json.dumps(profile), "owner": "true" if owner else "false",
                        "pfx": json.dumps(pfx), "lpfx": json.dumps(lpfx), "lp": self.lp, "wp": self.wp, "lsr": self.lsr}
        return _node(prog + "\nvar KEYS = " + json.dumps(list(KEYS)) + ";\n" + self.script + "\n" + SCENARIO)

    def _seed(self):
        return {"d2r_d2jsp_topic": TOPIC, "d2r_d2jsp_fg": json.dumps({"Grief": "10"}),
                "d2r_d2jsp_sold": json.dumps({}), "d2r_d2jsp_hide": json.dumps({}),
                "d2r_d2jsp_gear": json.dumps({}), "d2r_d2jsp_mods": json.dumps({"Grief": "+1 test"}),
                "d2r_d2jsp_log": json.dumps({})}

    def test_the_desk_keys_are_in_the_fork_set_and_parse(self):
        # the same quote-pairing read test_store_isolation uses on this Set - an apostrophe in a note breaks it
        blob = re.search(r"window\._LP_FORKED\s*=\s*new Set\(\[(.*?)\]\)", self.src, re.S).group(1)
        names = {a or b for a, b in re.findall(r"'([^']+)'|\"([^\"]+)\"", blob)}
        missing = [k for k in KEYS if k not in names]
        self.assertEqual(missing, [], "desk stores missing from window._LP_FORKED (or a note broke the quote pairing)")
        head = blob[:blob.index("d2r_vaultRemoved")]
        for k in KEYS:
            self.assertIn(k, head, "%s is not in the desk block at the head of the Set" % k)
        self.assertIn("const LS = window.LSR;", self.src)
        self.assertIn("try { if (typeof LS !== 'undefined' && LS && LS.getItem) return LS; } catch (e) {}", self.src)

    def test_owner_ladder_writes_under_its_own_prefix_and_starts_empty(self):
        o = self._world("ladder", True, self._seed())
        for k in KEYS:
            self.assertEqual(o["keys"][k], "L·" + k)
        raw = o["raw"]
        self.assertEqual(json.loads(raw["L·d2r_d2jsp_fg"]), {"Grief": "77"}, "a ladder price did not land on L·")
        self.assertEqual(json.loads(raw["L·d2r_d2jsp_hide"]), {"Shako": 1})
        self.assertEqual(json.loads(raw["d2r_d2jsp_fg"]), {"Grief": "10"}, "a ladder price overwrote main's")
        self.assertEqual(json.loads(raw["d2r_d2jsp_hide"]), {}, "a ladder removal hid the item on main")
        self.assertEqual(raw["d2r_d2jsp_topic"], TOPIC)
        self.assertNotIn("L·d2r_d2jsp_topic", raw, "main's topic was copied onto ladder")
        self.assertNotIn('value="10"', o["card"], "main's typed price fills the ladder card")
        self.assertNotIn("+1 test", o["card"], "main's mods fill the ladder card")
        notes = [s for s in o["said"] if s.startswith("Ladder keeps its own trade list")]
        self.assertEqual(len(notes), 1, "the ladder notice is said %d times over two opens" % len(notes))

    def test_owner_main_keeps_the_bare_values(self):
        o = self._world("main", True, self._seed())
        for k in KEYS:
            self.assertEqual(o["keys"][k], k)
        raw = o["raw"]
        self.assertEqual(json.loads(raw["d2r_d2jsp_fg"]), {"Grief": "77"})
        self.assertEqual(json.loads(raw["d2r_d2jsp_hide"]), {"Shako": 1})
        self.assertFalse([k for k in raw if "·" in k], "the owner main wrote a prefixed key: %r" % sorted(raw))
        self.assertIn('value="10"', o["card"], "main lost its own typed price")
        self.assertFalse([s for s in o["said"] if s.startswith("Ladder keeps")], "main is told the ladder notice")

    def test_a_guest_main_keeps_what_it_wrote_and_a_guest_ladder_starts_empty(self):
        g = self._world("main", False, self._seed())
        pre = "I·abcd1234·"
        for k in KEYS:
            self.assertEqual(g["keys"][k], pre + k)
            self.assertEqual(g["afterLoad"].get(pre + k), self._seed()[k], "%s was not kept by the guest main" % k)
        self.assertIn('value="10"', g["card"])
        self.assertEqual(json.loads(g["raw"][pre + "d2r_d2jsp_fg"]), {"Grief": "77"})
        lad = self._world("ladder", False, self._seed())
        lpre = "IL·abcd1234·"
        self.assertFalse([k for k in lad["afterLoad"] if k.startswith(lpre) or k.startswith(pre)],
                         "a guest ladder copied the bare desk values: %r" % sorted(lad["afterLoad"]))
        own = self._seed()
        own[pre + "d2r_d2jsp_topic"] = "https://forums.d2jsp.org/topic.php?t=2&f=268"
        kept = self._world("main", False, own)
        self.assertEqual(kept["afterLoad"][pre + "d2r_d2jsp_topic"], "https://forums.d2jsp.org/topic.php?t=2&f=268",
                         "the guest copy wrote over a topic its own world already held")


POST_THE_LIST = r"""
(async function(){
  var out = { afterLoad: JSON.parse(JSON.stringify(RAW)) };
  window._d2jspShow();
  for (var i = 0; i < 4; i++) await flush();
  if (typeof BEFORE_POST === 'function') BEFORE_POST();
  var b = { getAttribute: function(k){ return ({ 'data-d2jsp-shop': '1', 'data-d2jsp-send': '1' })[k] || null; } };
  b.closest = function(sel){ return (sel === '#tab-d2jsp' || sel === '[data-d2jsp-shop]') ? b : null; };
  // the first click paints the draft the room built; it is mirrored into the draft host, then the second click sends it
  LISTEN.click[0]({ target: b, preventDefault: function(){} });
  var html = NODES['d2jsp-draft-host']._html;
  var un = function(t){ return t.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&'); };
  VIEW.textContent = un((html.match(/data-d2jsp-draft-view[^>]*>([\s\S]*?)<\/pre>/) || [])[1] || '');
  SUBJECT.textContent = un((html.match(/data-d2jsp-draft-subject[^>]*>([\s\S]*?)<\/p>/) || [])[1] || '');
  LISTEN.click[0]({ target: b, preventDefault: function(){} });
  for (var j = 0; j < 6; j++) await flush();
  out.sent = SENT;
  out.raw = RAW;
  process.stdout.write(JSON.stringify(out));
})().catch(function(e){ process.stderr.write(String(e && e.stack || e)); process.exit(1); });
"""

LADDER_TOPIC = "https://forums.d2jsp.org/topic.php?t=777&f=271"


@unittest.skipUnless(NODE, "node is required to run the router and the room")
class TheLiveLadderTopicFollowsTheLadder(unittest.TestCase):
    """The bare topic is the ladder topic when it names board 271: it goes to ladder, never to main."""

    @classmethod
    def setUpClass(cls):
        TheD2jspDeskForksWithTheProfile.setUpClass.__func__(cls)

    _world = TheD2jspDeskForksWithTheProfile._world

    def _post(self, profile, owner, raw, answer=None, before=""):
        pfx = "" if owner else "I·abcd1234·"
        lpfx = "L·" if owner else "IL·abcd1234·"
        prog = WORLD % {"raw": json.dumps(raw), "profile": json.dumps(profile), "owner": "true" if owner else "false",
                        "pfx": json.dumps(pfx), "lpfx": json.dumps(lpfx), "lp": self.lp, "wp": self.wp, "lsr": self.lsr}
        head = "var SEND_ANSWER = %s;\nvar BEFORE_POST = %s;\n" % (json.dumps(answer), before or "null")
        return _node(head + prog + "\n" + self.script + "\n" + POST_THE_LIST)

    def _seed(self, topic):
        return {"d2r_d2jsp_topic": topic, "d2r_d2jsp_fg": json.dumps({"Grief": "10", "Shako": "5"}),
                "d2r_d2jsp_sold": "{}", "d2r_d2jsp_hide": "{}", "d2r_d2jsp_gear": "{}", "d2r_d2jsp_mods": "{}",
                "L·d2r_d2jsp_fg": json.dumps({"Grief": "12", "Shako": "6"}),
                "IL·abcd1234·d2r_d2jsp_fg": json.dumps({"Grief": "12", "Shako": "6"})}

    def test_the_owner_ladder_updates_its_live_271_topic(self):
        o = self._post("ladder", True, self._seed(LADDER_TOPIC))
        self.assertEqual(o["afterLoad"].get("L·d2r_d2jsp_topic"), LADDER_TOPIC,
                         "the ladder did not take its own live 271 topic from the bare key")
        self.assertEqual(len(o["sent"]), 1, "the list post did not reach the console")
        self.assertEqual(o["sent"][0]["forum"], 271)
        self.assertEqual(o["sent"][0].get("topic"), LADDER_TOPIC,
                         "the next ladder list post opens a second 271 topic while the first is live")
        self.assertEqual(o["raw"]["d2r_d2jsp_topic"], LADDER_TOPIC, "the bare key was moved, so an older build loses it")

    def test_a_guest_ladder_takes_it_into_its_own_namespace(self):
        o = self._post("ladder", False, self._seed(LADDER_TOPIC))
        self.assertEqual(o["afterLoad"].get("IL·abcd1234·d2r_d2jsp_topic"), LADDER_TOPIC)
        self.assertEqual(o["sent"][0].get("topic"), LADDER_TOPIC)
        copied = [k for k in o["afterLoad"] if k.startswith("IL·abcd1234·") and k != "IL·abcd1234·d2r_d2jsp_topic"
                  and k not in self._seed(LADDER_TOPIC)]
        self.assertEqual(copied, [], "a guest ladder copied bare filings: %r" % copied)

    def test_a_271_topic_never_lands_in_a_main_key(self):
        g = self._world("main", False, self._seed(LADDER_TOPIC))
        self.assertNotIn("I·abcd1234·d2r_d2jsp_topic", g["afterLoad"], "a guest main adopted the ladder topic")
        self.assertEqual(g["afterLoad"].get("I·abcd1234·d2r_d2jsp_fg"), json.dumps({"Grief": "10", "Shako": "5"}),
                         "the guest main stopped keeping its own filings")
        m = self._post("main", True, self._seed(LADDER_TOPIC))
        # M6 T2 review: the owner main saves the live 271 topic into the LADDER key on load (never a main key)
        self.assertEqual(m["afterLoad"].get("L·d2r_d2jsp_topic"), LADDER_TOPIC,
                         "the owner main left the live 271 topic only in the bare key it is about to overwrite")
        self.assertEqual(m["afterLoad"]["d2r_d2jsp_topic"], LADDER_TOPIC, "the bare key was moved, so an older build loses it")
        self.assertEqual(m["sent"][0]["forum"], 268)
        self.assertNotIn("topic", m["sent"][0], "a main list post was aimed at the ladder topic")

    def test_a_main_post_first_after_the_update_keeps_the_live_ladder_topic(self):
        # M6 T2 review: ladder posted last, so the bare key holds the live 271 topic, and his first list post after
        # the update is on main. The main receipt writes the bare key; the next ladder list post must still update 271.
        main_topic = "https://forums.d2jsp.org/topic.php?t=900&f=268"
        m = self._post("main", True, self._seed(LADDER_TOPIC),
                       answer={"ok": True, "reason": "submitted", "board": 268, "topic": main_topic})
        self.assertEqual(m["raw"]["d2r_d2jsp_topic"], main_topic, "the main receipt did not save the main topic")
        self.assertEqual(m["raw"].get("L·d2r_d2jsp_topic"), LADDER_TOPIC, "the main post erased the live ladder topic")
        lad = self._post("ladder", True, m["raw"])
        self.assertEqual(lad["sent"][0]["forum"], 271)
        self.assertEqual(lad["sent"][0].get("topic"), LADDER_TOPIC,
                         "the next ladder list post opens a second 271 topic while the first is live")

    def test_a_271_topic_saved_bare_after_the_main_page_loaded_is_kept_too(self):
        # a page still on an older build (another tab, on ladder) posts while this main page is open: its 271 topic
        # lands bare after this page's load rescue ran, so the main receipt must rescue it before it overwrites it
        main_topic = "https://forums.d2jsp.org/topic.php?t=901&f=268"
        late = "function(){ RAW['d2r_d2jsp_topic'] = %s; }" % json.dumps(LADDER_TOPIC)
        m = self._post("main", True, self._seed(TOPIC),
                       answer={"ok": True, "reason": "submitted", "board": 268, "topic": main_topic}, before=late)
        self.assertNotIn("L·d2r_d2jsp_topic", m["afterLoad"], "a board 268 topic was copied onto ladder")
        self.assertEqual(m["raw"]["d2r_d2jsp_topic"], main_topic)
        self.assertEqual(m["raw"].get("L·d2r_d2jsp_topic"), LADDER_TOPIC,
                         "the main receipt overwrote a live 271 topic an older build saved after this page loaded")

    def test_a_ladder_topic_already_saved_is_never_replaced(self):
        own = self._seed(LADDER_TOPIC)
        own["L·d2r_d2jsp_topic"] = "https://forums.d2jsp.org/topic.php?t=888&f=271"
        o = self._post("ladder", True, own)
        self.assertEqual(o["afterLoad"]["L·d2r_d2jsp_topic"], "https://forums.d2jsp.org/topic.php?t=888&f=271")
        self.assertEqual(o["sent"][0].get("topic"), "https://forums.d2jsp.org/topic.php?t=888&f=271")
        main_topic = self._post("ladder", True, self._seed(TOPIC))
        self.assertNotIn("L·d2r_d2jsp_topic", main_topic["afterLoad"], "a board 268 topic was copied onto ladder")
        self.assertNotIn("topic", main_topic["sent"][0])


RED_PROOF = [
    {"why": "#114 - the six desk stores leave the fork set, so main and ladder share one saved topic again",
     "file": "bible.html",
     "find": "  'd2r_d2jsp_topic', 'd2r_d2jsp_fg', 'd2r_d2jsp_sold', 'd2r_d2jsp_hide', 'd2r_d2jsp_gear', 'd2r_d2jsp_mods',\n",
     "replace": "",
     "matches": 1},
    {"why": "#114 - the desk store skips the router, so a ladder write lands on the bare main key",
     "file": "bible.html",
     "find": "    try { if (typeof LS !== 'undefined' && LS && LS.getItem) return LS; } catch (e) {}\n    try { return localStorage; } catch (e2) { return null; }\n",
     "replace": "    try { return localStorage; } catch (e2) { return null; }\n",
     "matches": 1},
    {"why": "#114 - the guest copy runs on ladder too, so main filings land on board 271",
     "file": "bible.html",
     "find": "      if (window.D2R_PROFILE === 'ladder') return;\n      if (window._D2R_OWNER) return;\n",
     "replace": "      if (window._D2R_OWNER) return;\n",
     "matches": 1},
    {"why": "#114 - the guest copy writes over a value its own world already holds",
     "file": "bible.html",
     "find": "        if (to === k || R.raw.getItem(to) != null) return;",
     "replace": "        if (to === k) return;",
     "matches": 1},
    {"why": "#114 - a guest main no longer keeps the filings it wrote before the fork",
     "file": "bible.html",
     "find": "        if (was == null) return;\n",
     "replace": "        return;\n",
     "matches": 1},
    {"why": "#114 - the ladder strands its live 271 topic, so its next list post opens a second topic on board 271",
     "file": "bible.html",
     "find": "      if (!R.raw.getItem(lt) && d2jspTopicBoard(bare) === D2JSP_LADDER_BOARD) R.raw.setItem(lt, String(bare));\n",
     "replace": "",
     "matches": 1},
    {"why": "#114 - the ladder copy writes over a ladder topic it already saved",
     "file": "bible.html",
     "find": "!R.raw.getItem(lt) && d2jspTopicBoard(bare)",
     "replace": "d2jspTopicBoard(bare)",
     "matches": 1},
    {"why": "#114 - a main topic (board 268) is copied onto ladder",
     "file": "bible.html",
     "find": "d2jspTopicBoard(bare) === D2JSP_LADDER_BOARD) R.raw.setItem(lt, String(bare));",
     "replace": "d2jspTopicBoard(bare) > 0) R.raw.setItem(lt, String(bare));",
     "matches": 1},
    {"why": "#114 - a guest main adopts the ladder topic into a main key",
     "file": "bible.html",
     "find": "        if (k === 'd2r_d2jsp_topic' && d2jspTopicBoard(was) === D2JSP_LADDER_BOARD) return;\n",
     "replace": "",
     "matches": 1},
    {"why": "M6 T2 review - the rescue runs only on a ladder load, so a main post first after the update erases the live 271 topic",
     "file": "bible.html",
     "find": "      rescueLadderTopic();\n      if (window.D2R_PROFILE === 'ladder') return;\n",
     "replace": "      if (window.D2R_PROFILE === 'ladder') { rescueLadderTopic(); return; }\n",
     "matches": 1},
    {"why": "M6 T2 review - the main receipt overwrites a 271 topic saved bare after this page loaded",
     "file": "bible.html",
     "find": "        if (window.D2R_PROFILE !== 'ladder') rescueLadderTopic();\n",
     "replace": "",
     "matches": 1},
    {"why": "M6 T2 review - the rescue copies the 271 topic into a MAIN key on the owner main",
     "file": "bible.html",
     "find": "      var lt = window._D2R_LPFX + 'd2r_d2jsp_topic';\n",
     "replace": "      var lt = R.key('d2r_d2jsp_topic');\n",
     "matches": 1},
    {"why": "#114 - the ladder notice is never said",
     "file": "bible.html",
     "find": "    if (ladderSaid || d2jspBoard() !== D2JSP_LADDER_BOARD) return;\n",
     "replace": "    return;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
