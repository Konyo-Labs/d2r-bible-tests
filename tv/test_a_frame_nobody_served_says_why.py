# -*- coding: utf-8 -*-
"""REG-3291 (#58) - A THEATRE FRAME NOBODY COULD SERVE SAYS WHY; IT NEVER DRAWS A BROKEN PICTURE.

GrokBot's live look on #230 (6655590795): Dean offline, the Vault stayed LOCKED, and the instant-replay frames showed
broken images (naturalWidth 0). The rule from #237: a missing owner frame must SAY WHY, never draw a broken box.
control_ui.html's thShowFrame handed the probe's error to the same `land` as its load, so the failed URL went on stage.
Held here by driving the page's own thShowFrame in node:
  * a frame that loads lands on the film as before;
  * one that fails leaves the film with NO src, dimmed, and the reason on its hover and on the caption -
    "the owner's console did not serve this picture" in a shadow, "not on this PC" on his own;
  * a later frame that loads clears the reason.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

HARNESS = r"""
var els = {};
function mk(id){ return els[id] = els[id] || { id: id, attrs: {}, style: {}, title: '', textContent: '', innerHTML: '',
  classList: { add: function(){}, remove: function(){}, toggle: function(){} },
  setAttribute: function (k, v) { this.attrs[k] = String(v); }, getAttribute: function (k) { return this.attrs[k] == null ? null : this.attrs[k]; },
  removeAttribute: function (k) { delete this.attrs[k]; if (k === 'src') this.src = ''; } }; }
var $ = function (id) { return mk(id); };
var _thPool = [{ src: '', complete: false }];
var _thPend = function () {};
var SHADOW = __SHADOW__;
var _consoleShadowUp = function () { return SHADOW; };
var setTimeout = function () {};
""" + "__FN__" + r"""
var out = {};
var film = mk('th-film'), cap = mk('th-caption');
thShowFrame('/hist/reel_a/f_1.jpg?w=1280'); _thPool[0].onload();
out.loaded = { src: film.src || '', missing: film.getAttribute('data-missing') };
thShowFrame('/hist/reel_a/f_2.jpg?w=1280'); _thPool[0].onerror();
out.failed = { src: film.src || '', missing: film.getAttribute('data-missing'), title: film.title, opacity: film.style.opacity, cap: cap.innerHTML };
_thPool[0].src = '';
thShowFrame('/hist/reel_a/f_3.jpg?w=1280'); _thPool[0].onload();
out.after = { src: film.src || '', missing: film.getAttribute('data-missing') };
process.stdout.write(JSON.stringify(out));
"""


class AFrameNobodyServedSaysWhy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which("node")
        if not node:
            raise unittest.SkipTest("no node - the theatre's frame loader is not driven here (UNMEASURED)")
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            ui = fh.read()
        a = ui.index("  function thShowFrame(url){")
        b = ui.index("  function thPreload(){", a)
        cls.out = {}
        for shadow in (True, False):
            prog = HARNESS.replace("__FN__", ui[a:b]).replace("__SHADOW__", "true" if shadow else "false")
            r = subprocess.run([node, "-"], input=prog, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                raise AssertionError("node failed: " + r.stderr[-1500:])
            cls.out[shadow] = json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_frame_that_loads_lands(self):
        self.assertEqual(self.out[False]["loaded"]["src"], "/hist/reel_a/f_1.jpg?w=1280")
        self.assertIsNone(self.out[False]["loaded"]["missing"])

    def test_a_frame_nobody_served_draws_no_broken_picture_and_says_why(self):
        f = self.out[True]["failed"]
        self.assertEqual(f["src"], "", "the failed URL went on the stage - a broken picture (#58)")
        self.assertIn("owner", f["missing"], "a shadow's missing frame does not say its owner did not serve it")
        self.assertIn(f["missing"], f["title"])
        self.assertIn(f["missing"], f["cap"], "the caption does not say why")
        self.assertIn("not on this PC", self.out[False]["failed"]["missing"])

    def test_a_later_frame_clears_the_reason(self):
        a = self.out[True]["after"]
        self.assertEqual(a["src"], "/hist/reel_a/f_3.jpg?w=1280")
        self.assertIsNone(a["missing"], "a frame that loaded still wears the last one's reason")


RED_PROOF = [
    {"why": "REG-3291 - a frame nobody served goes on the stage as a broken picture again",
     "file": "tv/control_ui.html",
     "find": "      film.removeAttribute('src'); film.__url = url; _thPend(film, false);\n      film.style.opacity = .25;\n",
     "replace": "      film.src = url; film.__url = url; _thPend(film, false);\n      film.style.opacity = .25;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3291 - the reason is never said",
     "file": "tv/control_ui.html",
     "find": "      film.setAttribute('data-missing', why);\n",
     "replace": "\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3291 - a loaded frame keeps the last one's reason",
     "file": "tv/control_ui.html",
     "find": "    film.removeAttribute('data-missing');\n",
     "replace": "\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
