# -*- coding: utf-8 -*-
"""REG-2959 (#51, GrokBot #230 tick 403) - THE THEATRE PAINTS THE PICTURE ITS LABEL NAMES, OR SAYS IT IS STILL LOADING.

GrokBot: reopening Session 175 in the Theatre painted a different picture (a character by a cart) under the same label
"8/67 · 7:54:44 PM.859" that first showed the game menu. thPaint writes a frame's label at once; the film follows when
that frame's picture has loaded (thShowFrame and its probe image). Measured on the shipped thShowFrame, cut from
control_ui.html and run in node over stub images:

  * a step back to the frame already on the film returned before it re-aimed what the film wants, so the probe still
    loading the frame stepped past landed afterwards and painted ITS picture under this frame's label;
  * while a frame not yet loaded is fetched (a first open asks the server to make each frame's 1280 copy), the film kept
    the previous picture under the new label and nothing said so.

Now the step back re-aims the film, a late probe for a frame no longer wanted paints nothing, and a frame still loading
after a beat dims the old picture (th-pending) until its own lands. A load inside the beat dims nothing (no flicker in
playback), a frame already decoded in the prefetch pool lands at once, and a frame that fails to load still ends the
wait. Fixtures only: stub images, no reel, no footage. RED_PROOF below.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
CUT = ("  var _thPool = [new Image(), new Image(), new Image(), new Image(), new Image()];", "\n  function thPreload(){")


def _cut():
    with open(UI, encoding="utf-8") as f:
        s = f.read()
    a, b = CUT
    if s.count(a) != 1:
        raise AssertionError("anchor %r matched %d times - re-point this law" % (a[:50], s.count(a)))
    i = s.index(a)
    j = s.index(b, i)
    fn = s[i:j]
    if fn.count("{") != fn.count("}"):
        raise AssertionError("the cut is not whole functions")
    return fn


PROG = r"""
var TIMERS = [];
var setTimeout = function(f, ms){ TIMERS.push(f); return TIMERS.length; };
function flush(){ var t = TIMERS.splice(0); t.forEach(function(f){ f(); }); }
function Image(){ this.complete = false; this._src = ''; this.onload = null; this.onerror = null; }
Object.defineProperty(Image.prototype, 'src', { get: function(){ return this._src; },
  set: function(v){ this._src = 'http://127.0.0.1:17999' + v; this.complete = false; } });
function cls(){ var set = {}; return { toggle: function(c, on){ if (on) set[c] = 1; else delete set[c]; }, contains: function(c){ return !!set[c]; } }; }
/* REG-3291 (v3876) - thShowFrame clears a frame's 'data-missing' mark and may set one, so the stand-in film carries the
   attribute methods every element has (the v3876 pre-flight found it without them) */
var FILM = { src: '', classList: cls(), _attrs: {}, title: '', style: {},
  setAttribute: function(k, v){ this._attrs[k] = String(v); },
  getAttribute: function(k){ return k in this._attrs ? this._attrs[k] : null; },
  removeAttribute: function(k){ delete this._attrs[k]; if (k === 'src') this.src = ''; } };
function $(id){ return id === 'th-film' ? FILM : null; }
__CUT__
function load(i){ var p = _thPool[i]; p.complete = true; if (p.onload) p.onload(); }
function fail(i){ var p = _thPool[i]; if (p.onerror) p.onerror(); }
function state(){ return { src: FILM.src, want: FILM.__want, pending: FILM.classList.contains('th-pending') }; }
var A = '/hist/reel_s/f_1000.jpg?w=1280', B = '/hist/reel_s/f_2000.jpg?w=1280', C = '/hist/reel_s/f_3000.jpg?w=1280',
    D = '/hist/reel_s/f_4000.jpg?w=1280', E = '/hist/reel_s/f_5000.jpg?w=1280', F = '/hist/reel_s/f_6000.jpg?w=1280';
var OUT = {};
/* the race: A on the film, B asked and still loading, back to A, then B's probe lands */
thShowFrame(A); load(0); flush(); OUT.a = state();
thShowFrame(B); thShowFrame(A); load(0); flush(); OUT.race = state();
/* a slow load: C is still loading after the beat, so the old picture is marked; then C lands */
thShowFrame(C); flush(); OUT.slow = state(); load(0); OUT.slowLanded = state();
/* a quick load: D lands inside the beat, so nothing is dimmed */
thShowFrame(D); OUT.quickAsked = state(); load(0); flush(); OUT.quick = state();
/* the prefetch pool already holds E, decoded: it lands at once */
_thPool[2].src = E; _thPool[2].complete = true; thShowFrame(E); flush(); OUT.pool = state();
/* F fails to load: the wait still ends */
thShowFrame(F); flush(); fail(0); OUT.failed = state(); OUT.failedWhy = FILM.getAttribute('data-missing');
console.log(JSON.stringify(OUT));
"""


def _run():
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    r = subprocess.run([NODE, "-"], input=PROG.replace("__CUT__", _cut()), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        raise AssertionError("the shipped thShowFrame did not run in node: %s" % (r.stderr or r.stdout)[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


_OUT = {}


def measured():
    if not _OUT:
        _OUT.update(_run())
    return _OUT


A = "/hist/reel_s/f_1000.jpg?w=1280"
C = "/hist/reel_s/f_3000.jpg?w=1280"
D = "/hist/reel_s/f_4000.jpg?w=1280"
E = "/hist/reel_s/f_5000.jpg?w=1280"
F = "/hist/reel_s/f_6000.jpg?w=1280"


class ATheatreFramePaintsItsOwnPicture(unittest.TestCase):

    def test_a_late_probe_never_paints_over_the_frame_he_stepped_back_to(self):
        o = measured()
        self.assertEqual(o["a"]["src"], A, "the setup needs frame A on the film: %r" % o["a"])
        self.assertEqual(o["race"]["src"], A, "the frame stepped past landed late and painted over A's label: %r" % o["race"])
        self.assertEqual(o["race"]["want"], A)
        self.assertFalse(o["race"]["pending"])

    def test_a_frame_still_loading_is_marked_until_its_picture_lands(self):
        o = measured()
        self.assertTrue(o["slow"]["pending"], "the previous picture sat under the new label, unmarked: %r" % o["slow"])
        self.assertNotEqual(o["slow"]["src"], C, "the premise needs C still loading")
        self.assertEqual(o["slowLanded"], {"src": C, "want": C, "pending": False})

    def test_a_quick_load_a_decoded_frame_and_a_failed_load_dim_nothing(self):
        o = measured()
        self.assertFalse(o["quickAsked"]["pending"], "the film dimmed the moment a frame was asked - playback flickers: %r" % o["quickAsked"])
        self.assertEqual(o["quick"], {"src": D, "want": D, "pending": False}, "a load inside the beat flickered: %r" % o["quick"])
        self.assertEqual(o["pool"], {"src": E, "want": E, "pending": False}, "a decoded frame did not land at once: %r" % o["pool"])
        # REG-3291 (#58) - a picture nobody could serve is never put on the film (it drew a broken box); the wait still ends
        self.assertEqual(o["failed"], {"src": "", "want": F, "pending": False}, "a failed load left the wait on, or "
                         "put the picture that failed on the film: %r" % o["failed"])
        self.assertTrue(o.get("failedWhy"), "a frame nobody could serve does not say why")


RED_PROOF = [
    {"why": "REG-2959 - a step back to the frame on the film leaves the film wanting the frame stepped past",
     "file": "tv/control_ui.html",
     "find": "    if (film.__url === url){ film.__want = url; _thPend(film, false); return; }\n",
     "replace": "    if (film.__url === url){ _thPend(film, false); return; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2959 - a frame still loading after a beat is never marked",
     "file": "tv/control_ui.html",
     "find": "      setTimeout(function(){ if (film.__want === url && film.__url !== url) _thPend(film, true); }, 160);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2959 - a frame that lands leaves the old picture dimmed",
     "file": "tv/control_ui.html",
     "find": "    var land = function(){ if (film.__want === url){ film.src = url; film.__url = url; _thPend(film, false); } };\n",
     "replace": "    var land = function(){ if (film.__want === url){ film.src = url; film.__url = url; } };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2959 - every load dims the film, so playback flickers",
     "file": "tv/control_ui.html",
     "find": "_thPend(film, true); }, 160);",
     "replace": "_thPend(film, true); }, 160); _thPend(film, true);",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main()
