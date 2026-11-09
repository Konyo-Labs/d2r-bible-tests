# -*- coding: utf-8 -*-
"""v3890 (#186) - THE SHELF DOOR PUTS BACK THE LAYER IT LIVES IN; AN INVISIBLE REFUSAL NEVER HOLDS THE DOOR.

His live console, 11-09: four "The Shelf did not open - 0x0 - nothing is visible" refusals 13:30-14:31 (ui_faults.jsonl,
shelf-door-refused), and GrokBot's repro (#230 11-09 13:26): a chapter, then Esc or the small x, then THE SHELF -> a 0x0
panel with no x, Esc dead, only a reload; a stale reel, then tab switches -> 0x0 every press. #th-shelfov lives inside
#theatre inside .stage, which is display:none on the Sessions view. MEASURED 11-09 on a private console with the forced
state (theatre open, view back on Sessions / theatre layer hidden): old code refused "0x0" on the first press and needed
three; new code opens it on the first. Held here (the layout itself is held by tests/v3890_shelf_door_puts_back_its_layer
.spec.ts on GitHub):
  * _shelfRestoreLayer, cut from control_ui.html and run in node: off the Sessions view (through _toTVD), the theatre
    shown, theatre-open on, TH.open - and nothing changed on a view that is not Sessions;
  * _shelfLayerWords names the view, the theatre's state, the stage's display and the first hidden ancestor;
  * THE SHELF's door, on a 0x0 shelf, puts the layer back and measures again BEFORE refusing, and a refusal carries the
    layer's words;
  * a refusal whose own box is 0x0 tears the theatre down, so the next press opens from a clean state.
RED_PROOF below.
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402
import js_strip  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")


def _ui():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


def _cut(src):
    head = "  function _shelfLayerWords(){"
    tail = "  window._shelfRestoreLayer = _shelfRestoreLayer;\n"
    assert src.count(head) == 1 and src.count(tail) == 1, "PREMISE: the shelf layer helpers moved or doubled"
    return src[src.index(head):src.index(tail) + len(tail)]


PROGRAM = r"""
function el(id, extra){ var e = { id: id, hidden: false, className: '', tagName: 'DIV', parentElement: null, _display: 'block' };
  for (var k in (extra || {})) e[k] = extra[k]; return e; }
var BODY = el('body', { attrs: {}, cls: {} });
BODY.getAttribute = function(k){ return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null; };
BODY.setAttribute = function(k, v){ this.attrs[k] = String(v); };
BODY.removeAttribute = function(k){ delete this.attrs[k]; };
BODY.classList = { add: function(c){ BODY.cls[c] = 1; }, contains: function(c){ return !!BODY.cls[c]; } };
var STAGE = el('stage'), THEATRE = el('theatre'), OV = el('th-shelfov');
OV.parentElement = THEATRE; THEATRE.parentElement = STAGE; STAGE.parentElement = BODY;
var EL = { 'stage': STAGE, 'theatre': THEATRE, 'th-shelfov': OV };
function $(id){ return EL[id] || null; }
var document = { body: BODY };
var window = { getComputedStyle: function(e){ return { display: (e === STAGE && BODY.attrs['data-view'] === 'sessions') ? 'none' : e._display }; } };
function getComputedStyle(e){ return window.getComputedStyle(e); }
var TOTVD = 0;
window._toTVD = function(){ TOTVD++; BODY.removeAttribute('data-view'); };
var TH = { open: false };
CUT
var out = {};
BODY.setAttribute('data-view', 'sessions'); THEATRE.hidden = true; TH.open = false;
out.before = _shelfLayerWords();
_shelfRestoreLayer();
out.after = { view: BODY.getAttribute('data-view'), theatreHidden: THEATRE.hidden, open: TH.open, cls: !!BODY.cls['theatre-open'], toTVD: TOTVD };
out.afterWords = _shelfLayerWords();
TOTVD = 0; BODY.setAttribute('data-view', 'vault');
_shelfRestoreLayer();
out.vault = { view: BODY.getAttribute('data-view'), toTVD: TOTVD };
process.stdout.write(JSON.stringify(out));
"""


class TheShelfDoorPutsBackItsLayer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _ui()
        if not NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        r = subprocess.run([NODE, "-"], input=PROGRAM.replace("CUT", _cut(cls.src)), capture_output=True, text=True,
                           timeout=60)
        if r.returncode != 0:
            raise AssertionError("the cut did not run: %s" % r.stderr[-800:])
        cls.out = json.loads(r.stdout)

    def test_the_layer_comes_back_off_the_sessions_view(self):
        """* THE POINT - the state the traps leave (Sessions view, theatre layer hidden, TH shut) comes back whole"""
        self.assertIn("view sessions", self.out["before"])
        self.assertIn("stage none", self.out["before"])
        self.assertIn("hidden at #theatre", self.out["before"])
        a = self.out["after"]
        self.assertEqual((a["view"], a["theatreHidden"], a["open"], a["cls"], a["toTVD"]), (None, False, True, True, 1), a)
        self.assertIn("stage block", self.out["afterWords"])

    def test_a_view_that_is_not_sessions_is_left_alone(self):
        self.assertEqual(self.out["vault"], {"view": "vault", "toTVD": 0}, "the door moved him off a view that hides nothing")

    def test_the_door_puts_the_layer_back_before_it_refuses(self):
        code = js_strip.strip_js_comments(self.src)
        i = code.index("var _r = _ov.getBoundingClientRect();")
        block = code[i:code.index("var _cards = _ov.querySelectorAll('.sh-card').length;", i)]
        self.assertLess(block.index("_shelfRestoreLayer();"), block.index("throw new Error("),
                        "THE SHELF refuses a 0x0 shelf before giving it its layer back")
        self.assertIn("var _lay0 = _shelfLayerWords();", block)
        self.assertIn("' — nothing is visible ('", block)

    def test_an_invisible_refusal_tears_the_theatre_down(self):
        code = js_strip.strip_js_comments(self.src)
        i = code.index("  function _shelfRefused(err, openErr){")
        fn = code[i:code.index("  window._shelfRefused = _shelfRefused;", i)]
        self.assertIn("if (!_rr || _rr.width < 2 || _rr.height < 2) { if (ov) ov.hidden = true; thClose(); }", fn,
                      "a refusal nobody can see still holds the door open")


RED_PROOF = [
    {"why": "v3890 (#186) - the door refuses a 0x0 shelf without putting its layer back (his four refusals, 11-09)",
     "file": "tv/control_ui.html",
     "find": "        _shelfRestoreLayer();\n        try { thShelf(true); } catch (_e0) {}\n",
     "replace": "        try { thShelf(true); } catch (_e0) {}\n",
     "matches": 1},
    {"why": "v3890 (#186) - the layer stays on the Sessions view, where the stage is display:none",
     "file": "tv/control_ui.html",
     "find": "    try { if (document.body.getAttribute('data-view') === 'sessions' && typeof window._toTVD === 'function') window._toTVD(); } catch (e) {}\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#186) - the theatre layer stays hidden",
     "file": "tv/control_ui.html",
     "find": "    try { var th = $('theatre'); if (th) th.hidden = false; } catch (e) {}\n",
     "replace": "",
     "matches": 1},
    {"why": "v3890 (#186) - an invisible refusal holds the door again (no x, Esc dead, only a reload)",
     "file": "tv/control_ui.html",
     "find": "      if (!_rr || _rr.width < 2 || _rr.height < 2) { if (ov) ov.hidden = true; thClose(); }\n",
     "replace": "      if (!_rr || _rr.width < 2 || _rr.height < 2) { if (ov) ov.hidden = true; }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
