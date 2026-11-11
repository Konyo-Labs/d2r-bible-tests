# -*- coding: utf-8 -*-
"""#92 (GrokBot, v3653 sweep) - THE THEATRE'S MODE BUTTON STAYS SHORT; THE WHOLE SENTENCE IS ITS HOVER.

The #th-mode button carried a 97-character label ("⏱ REAL · all 20 photos · 1:1 time · 📹 film 12 (film-lane stills) ·
photos 20 (every framed beat)"), which pushed the theatre's controls at narrow widths. The film count stays beside the
photos in two words; the full #252 sentence moved to the button's title.

Driven in node: thModeLabel / thModePill / _filmShortSay / _filmPhotoSay cut from control_ui.html with a stub
thSessionPhotoStats - every mode's label is at most 60 characters and names the film count, the title carries the whole
sentence, a film count nobody measured is UNKNOWN, and equal counts add nothing.
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
NODE = shutil.which("node")

with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as _fh:
    UI = _fh.read()


def _fn(start):
    assert UI.count(start) == 1, start
    i = UI.index(start)
    return UI[i:UI.index("\n  }\n", i) + 4]


class TheTheatreModeButtonStaysShort(unittest.TestCase):

    def test_short_on_the_button_whole_in_the_hover(self):
        if not NODE:
            raise AssertionError("node is absent - this law cannot run here, so it is UNMEASURED")
        js = ("var STATS = null; function thSessionPhotoStats(){ return STATS; }\n"
              "var EL = { classList: { remove: function(){}, add: function(){} }, textContent: '', title: '' };\n"
              "function $(id){ return EL; }\n"
              "var document = { getElementById: function(){ return null; } };\n"
              + _fn("  function _filmPhotoSay(film, photos){") + "\n" + _fn("  function _filmShortSay(film){") + "\n"
              + _fn("  function thModeLabel(m){") + "\n" + _fn("  function _thModeSay(m){") + "\n" + _fn("  function thModePill(m){") + "\n"
              # v3898 (#209) - the hover now ends with what the count left out; the pill calls it, so the harness carries it
              + _fn("  function thLeftOutSay(st){") + "\n"
              "var out = {};\n"
              "STATS = { allFoot: 354, allPhoto: 397, curFoot: 354, curPhoto: 397 }; thModePill('real'); out.big = EL.textContent;\n"
              "STATS = { allFoot: 12, allPhoto: 20, curFoot: 12, curPhoto: 20 };\n"
              "['real', 'highlight', 'full'].forEach(function(m){ thModePill(m); out[m] = { label: EL.textContent, title: EL.title }; });\n"
              "STATS = { allFoot: null, allPhoto: 20, curFoot: 0, curPhoto: 20 }; thModePill('real'); out.unknown = EL.textContent;\n"
              "STATS = { allFoot: 20, allPhoto: 20, curFoot: 20, curPhoto: 20 }; thModePill('real'); out.same = { label: EL.textContent, title: EL.title };\n"
              "console.log(JSON.stringify(out));\n")
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        out = json.loads(r.stdout.strip().splitlines()[-1])
        for m in ("real", "highlight", "full"):
            self.assertLessEqual(len(out[m]["label"]), 34, "the %s label is %d characters: %r" % (m, len(out[m]["label"]), out[m]["label"]))
            self.assertIn("film 12", out[m]["label"])
            self.assertIn("photos 20 (every framed beat)", out[m]["title"], "the whole sentence left the hover: %r" % out[m])
        self.assertIn("film UNKNOWN", out["unknown"])
        self.assertNotIn("film", out["same"]["label"])
        # #92 (GrokBot v3817) - the reel he opened (397 photos, film 354) wrapped at ~45 characters; what a mode does is
        # in its hover now, and the label names the mode and its counts
        self.assertEqual(out["big"], "\u23f1 REAL \u00b7 397 photos \u00b7 \U0001f4f9 film 354", out["big"])
        self.assertEqual(out["same"]["title"], "REAL - every photo at 1:1 time", "the hover lost what the mode does")
        self.assertIn("1:1 time", out["real"]["title"])
        self.assertIn("time-zipped", out["full"]["title"])
        self.assertIn("centered on each AI read", out["highlight"]["title"])


RED_PROOF = [
    {"why": "#92 - the mode button carries the whole film sentence again (97 characters)",
     "file": "tv/control_ui.html",
     "find": "    var _fpExtra = (st.allFoot !== st.allPhoto) ? _filmShortSay(st.allFoot) : '';\n",
     "replace": "    var _fpExtra = (st.allFoot !== st.allPhoto) ? _filmPhotoSay(st.allFoot, st.allPhoto) : '';\n",
     "matches": 1, "needs": "node"},
    {"why": "#92 - the whole sentence is dropped instead of moved to the hover",
     "file": "tv/control_ui.html",
     "find": "          el.title = _thModeSay(m) + ((st.allFoot !== st.allPhoto) ? (' · film and photos differ' + _filmPhotoSay(st.allFoot, st.allPhoto)) : '')\n                     + thLeftOutSay(st); } catch (eTt) {}",
     "replace": "          void st; } catch (eTt) {}",
     "matches": 1, "needs": "node"},
    {"why": "#92 (GrokBot v3817) - the mode button carries what the mode does again, and wraps on a loaded reel",
     "file": "tv/control_ui.html",
     "find": "    return '\u23f1 REAL \u00b7 ' + (st.allPhoto || n) + ' photos' + _fpExtra;",
     "replace": "    return '\u23f1 REAL \u00b7 all ' + (st.allPhoto || n) + ' photos \u00b7 1:1 time' + _fpExtra;",
     "matches": 1, "needs": "node"},
    {"why": "#92 (GrokBot v3817) - what the mode does leaves the hover too",
     "file": "tv/control_ui.html",
     "find": "          el.title = _thModeSay(m) + ((st.allFoot",
     "replace": "          el.title = '' + ((st.allFoot",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
