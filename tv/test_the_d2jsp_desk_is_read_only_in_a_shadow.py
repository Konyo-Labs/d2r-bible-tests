# -*- coding: utf-8 -*-
"""#83 (REG-3095, GrokBot 06:36) - IN A SHADOW THE D2JSP DESK'S FG BOX IS READ ONLY, AND POST IS DISABLED, ON EVERY CARD.

GrokBot in the Mac's shadow: Mark sold, Remove from this list and Options changed nothing and sent nothing, and Post was
disabled - "Small gap: the 'Your fg' box still takes typing in the shadow (typed 99, nothing was sent)". The shadow veil
stops a typed key, yet a path with no key press reaches a writable box, so it read as editable on a page that sends nothing.
And Post was disabled there only because nothing was priced: the card disabled it for `send == null || sold`, so a priced
card in a shadow would have offered a Post the veil then swallowed. Now, in a shadow (the veil's handle window._tvdShadow,
else the shadow class - the shadow law's guard form), the fg box is readonly, says why, and Post is disabled; outside a
shadow both are exactly as before.

Driven: the D2JSP pane's own script cut out of bible.html and run in node over a fake page, rendering a priced card outside
a shadow, inside a snapshot shadow, and inside a shadow known only by its class - never a browser, never d2jsp. RED_PROOF
below.
"""
import json
import os
import shutil
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
NODE = shutil.which("node")
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")

FAKES = r"""
function Node(id){ this.id = id; this.attrs = {}; this.hidden = true; this._html = ''; this.textContent = ''; this.title = ''; }
Node.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); };
Node.prototype.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
Node.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
Node.prototype.querySelector = function(){ return { focus: function(){} }; };
Node.prototype.querySelectorAll = function(){ return []; };
Node.prototype.appendChild = function(){};
Node.prototype.insertBefore = function(){};
Object.defineProperty(Node.prototype, 'innerHTML', { get: function(){ return this._html; }, set: function(v){ this._html = String(v); } });
var NODES = {};
['d2jsp-list', 'd2jsp-status', 'd2jsp-lamp', 'd2jsp-draft-host', 'd2jsp-board'].forEach(function(id){ NODES[id] = new Node(id); });
var CLASSES = {};
var document = {
  documentElement: { classList: { contains: function(c){ return !!CLASSES[c]; } } },
  getElementById: function(id){ return NODES[id] || null; },
  querySelector: function(){ return null; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(){},
  createElement: function(){ return new Node(''); },
  body: { appendChild: function(){} }
};
var RAW = { 'd2r_d2jsp_fg': JSON.stringify({ 'Grief': '55' }) };
var localStorage = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAW, k) ? RAW[k] : null; },
                     setItem: function(k, v){ RAW[k] = String(v); }, removeItem: function(k){ delete RAW[k]; } };
var location = { hostname: '127.0.0.1' };
var MULE = JSON.stringify({ 'Grief': 'm1' });
var window = { addEventListener: function(){}, LSR: { getItem: function(k){ return k === 'd2r_muleAssign' ? MULE : null; } } };
function fetch(){ return Promise.resolve({ status: 200, json: function(){ return Promise.resolve({ state: 'unknown', fg: null, reason: 'no prices', n: 0 }); } }); }
"""

SCENARIO = r"""
function fg(html){ var m = html.match(/<input data-d2jsp-fg="Grief"[^>]*>/); return m ? m[0] : ''; }
function post(html){ var m = html.match(/<button[^>]*data-d2jsp-post="Grief"[^>]*>/); return m ? m[0] : ''; }
var out = {};
var h = window._d2jspCardHtml('Grief'); out.own = { fg: fg(h), post: post(h) };
window._tvdShadow = { owner: 'Konyo · Mac' };
h = window._d2jspCardHtml('Grief'); out.snap = { fg: fg(h), post: post(h) };
delete window._tvdShadow; CLASSES['tvd-shadow'] = true;
h = window._d2jspCardHtml('Grief'); out.cls = { fg: fg(h), post: post(h) };
process.stdout.write(JSON.stringify(out));
"""


def _between(src, start, end):
    i = src.index(start)
    return src[i + len(start):src.index(end, i + len(start))]


class TheD2jspDeskIsReadOnlyInAShadow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        with open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        pane = _between(src, 'id="tab-d2jsp"', 'id="tab-vault"')
        code = pane.split("<script>", 1)[1].split("</script>", 1)[0]
        r = subprocess.run([NODE, "-"], input=FAKES + code + "\n" + SCENARIO, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the D2JSP pane did not run in node: %s" % r.stderr[-900:])
        cls.o = json.loads(r.stdout)

    def test_premise_the_card_and_its_controls_are_drawn(self):
        for k in ("own", "snap", "cls"):
            self.assertTrue(self.o[k]["fg"] and self.o[k]["post"], "premise: no fg box or Post on the %s card: %r" % (k, self.o[k]))

    def test_outside_a_shadow_the_box_takes_typing_and_a_priced_post_is_live(self):
        self.assertNotIn("readonly", self.o["own"]["fg"])
        self.assertNotIn("disabled", self.o["own"]["post"], "premise: a priced card's Post is not live outside a shadow")

    def test_in_a_snapshot_shadow_the_box_is_read_only_and_post_is_disabled(self):
        self.assertIn(" readonly ", self.o["snap"]["fg"], "the fg box takes typing in a shadow")
        self.assertIn('aria-readonly="true"', self.o["snap"]["fg"])
        self.assertIn("this is their console, shown in a shadow", self.o["snap"]["fg"])
        self.assertIn(" disabled", self.o["snap"]["post"], "a priced card offered Post in a shadow")

    def test_a_shadow_known_only_by_its_class_is_read_only_too(self):
        self.assertIn(" readonly ", self.o["cls"]["fg"])
        self.assertIn(" disabled", self.o["cls"]["post"])


RED_PROOF = [
    {"why": "REG-3095 - the fg box takes typing in a shadow again",
     "file": "bible.html",
     "find": "        + (inShadow() ? ' readonly aria-readonly=\"true\" title=\"Read only: this is their console, shown in a shadow\"' : '')\n",
     "replace": "        + ''\n",
     "matches": 1},
    {"why": "REG-3095 - a priced card offers Post in a shadow again",
     "file": "bible.html",
     "find": "((send == null || sold || inShadow()) ? ' disabled' : '')",
     "replace": "((send == null || sold) ? ' disabled' : '')",
     "matches": 1},
    {"why": "REG-3095 - the guard misses a shadow known only by its class",
     "file": "bible.html",
     "find": "  function inShadow(){\n    if (window._tvdShadow) return true;\n    try { return document.documentElement.classList.contains('tvd-shadow'); } catch (e) { return false; }\n",   # ship-chain: REG-3105's _flShadow carries the same line, so the guard is named by its function
     "replace": "  function inShadow(){\n    if (window._tvdShadow) return true;\n    return false;\n",
     "matches": 1},
    {"why": "REG-3095 - the guard misses the veil's own handle",
     "file": "bible.html",
     "find": "  function inShadow(){\n    if (window._tvdShadow) return true;\n",
     "replace": "  function inShadow(){\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
