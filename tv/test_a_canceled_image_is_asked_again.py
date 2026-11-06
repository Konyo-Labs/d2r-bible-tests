# -*- coding: utf-8 -*-
"""REG-3255 (#73) - AN IMAGE WHOSE LOAD THE ENGINE FRAME CANCELED IS ASKED AGAIN, ONCE.

MEASURED on the work ALT (headless Chrome, 1920 wide, GETs only, 2026-11-06): every /art/ request the engine iframe
starts ends net::ERR_ABORTED, because the first status poll re-points the frame from v=boot to the version and it is
navigated once more after. Blink shares one in-flight image load between documents, so the console's own #hero, header
tab icons and rune icons - asking for the same files at that moment - inherit the cancel and are left broken with no
error event: complete, naturalWidth 0, their onerror never runs. 4-9 broken per load on the ALT; GrokBot counted Mac 4-8
and ALT 6-16. Re-asking each such image once took 9, 7 and 5 broken to 0 on the ALT's own page.

This law drives the SHIPPED script block in node against a fake document. RED_PROOF below.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass
UI = os.path.join(HERE, "control_ui.html")
START = "/* REG-3255 (#73) - AN IMAGE WHOSE LOAD THE ENGINE FRAME CANCELED IS ASKED AGAIN, ONCE."
END = "})();   /* ⟦REG-3255 END⟧ */"


def _block():
    with io.open(UI, encoding="utf-8") as fh:
        src = fh.read()
    i = src.find(START)
    assert i >= 0, "the re-ask block is gone from the console"
    j = src.find(END, i)
    assert j > i, "the re-ask block's end is gone"
    return src[i:j + len("})();")]   # the IIFE, up to its own end marker


HARNESS = r"""
var listeners = {frame: [], window: []}, timers = [];
function Img(src, complete, w, extra) {
  var a = {src: src}; if (extra) for (var k in extra) a[k] = extra[k];
  return {complete: complete, naturalWidth: w, _a: a, _set: [],
          getAttribute: function (k) { return k in this._a ? this._a[k] : null; },
          setAttribute: function (k, v) { this._a[k] = String(v); },
          set src(v) { this._set.push(v); this._a.src = v; this.complete = false; },
          get src() { return this._a.src; }};
}
var images = %(images)s.map(function (r) { return Img(r[0], r[1], r[2], r[3]); });
var document = {images: images, getElementById: function (id) {
  return id === 'tvd-eng' ? {addEventListener: function (ev, fn) { if (ev === 'load') listeners.frame.push(fn); }} : null; }};
var window = {addEventListener: function (ev, fn) { if (ev === 'load') listeners.window.push(fn); }};
function setTimeout(fn, ms) { timers.push(fn); }
%(block)s
var out = {wired: {frame: listeners.frame.length, window: listeners.window.length}, passes: []};
function fire(list) { list.forEach(function (fn) { fn(); }); var t = timers.splice(0); t.forEach(function (fn) { fn(); }); }
fire(listeners.frame);
out.passes.push(images.map(function (im) { return im._set.slice(); }));
images.forEach(function (im) { if (im._set.length) { im.complete = true; im.naturalWidth = 0; } });   /* canceled again */
fire(listeners.window);
out.passes.push(images.map(function (im) { return im._set.slice(); }));
console.log(JSON.stringify(out));
"""


class ACanceledImageIsAskedAgain(unittest.TestCase):

    def drive(self, images):
        js = HARNESS % {"images": json.dumps(images), "block": _block()}
        fd, p = tempfile.mkstemp(prefix=".reask_drive_", suffix=".js", dir=HERE)
        try:
            with io.open(fd, "w", encoding="utf-8") as fh:
                fh.write(js)
            r = subprocess.run(["node", p], capture_output=True, text=True, timeout=60)
        except FileNotFoundError:   # REG-1900 - the ONE skip: no node here
            self.skipTest("node unavailable - a skip is NOT a pass")
        finally:
            try:
                os.unlink(p)
            except OSError:
                pass
        self.assertEqual(r.returncode, 0, "the shipped block threw:\n%s" % (r.stderr or "")[-800:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_it_runs_after_every_engine_frame_load_and_the_page_load(self):
        out = self.drive([])
        self.assertEqual(out["wired"], {"frame": 1, "window": 1}, out)

    def test_a_canceled_image_is_asked_again_once(self):
        out = self.drive([["/art/ui_tab_forge.png", True, 0], ["/art/hd_ber_rune.png?w=2", True, 0]])
        self.assertEqual(out["passes"][0], [["/art/ui_tab_forge.png?reask=1"], ["/art/hd_ber_rune.png?w=2&reask=1"]],
                         "a canceled image stayed broken: %r" % out)
        self.assertEqual(out["passes"][1], out["passes"][0], "an image was asked again on every pass: %r" % out)

    def test_loaded_loading_and_inline_images_are_left_alone(self):
        out = self.drive([["/art/a.png", True, 96], ["/art/b.png", False, 0], ["data:image/png;base64,AAAA", True, 0],
                          ["", True, 0]])
        self.assertEqual(out["passes"][1], [[], [], [], []], out)


RED_PROOF = [
    {"why": "REG-3255 - a canceled image is never asked again, so the hero and header icons stay broken on a slow console",
     "file": "tv/control_ui.html",
     "find": "        im.src = src + (src.indexOf('?') < 0 ? '?' : '&') + 'reask=1';\n",
     "replace": "        void src;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3255 - an image is asked again on every pass, so a file that is really missing is asked forever",
     "file": "tv/control_ui.html",
     "find": "im.naturalWidth !== 0 || im.getAttribute('data-reasked')) return;\n",
     "replace": "im.naturalWidth !== 0) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3255 - the re-ask runs only at page load, never after the engine frame's navigation that cancels the loads",
     "file": "tv/control_ui.html",
     "find": "    if (eng) eng.addEventListener('load', function () { setTimeout(_reaskCanceledImages, 1500); });\n",
     "replace": "    void eng;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3255 - a loaded image is asked again too",
     "file": "tv/control_ui.html",
     "find": "        if (!im || !im.complete || im.naturalWidth !== 0 || ",
     "replace": "        if (!im || !im.complete || ",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
