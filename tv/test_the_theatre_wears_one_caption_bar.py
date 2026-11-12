# -*- coding: utf-8 -*-
"""v3903 (#210, his approved design brief - GrokBot #230 6795098365 ask 3) - CLEAN THEATRE: ONE THIN CAPTION BAR.

The brief: "the image fills the stage with one thin caption bar (like frame 2/395, the Loading splash); status lines, the AI
read box and the rest move into a collapsible side/bottom panel, closed by default". The caption stacked, per beat, a retro
hand-off row, the READ/MISS verdict, forensic flags, the photo position and clock, the AI-stamp hint AND the whole AI read card
(CAPTURE / AI READ / IT SAW / OCR / the three-eye dossier) plus name chips - up to 44vh climbing over the film. The read panel
(#th-drawer) already carries each of those in full, and it never opens itself (test_the_shelf_opens_on_the_list).

Now: the caption is one line (thCaptionBar - the whole text on hover), thCaption(b, 'bar') is the beat's identity line
("read #N · where · photo lock · flags") and thCaption(b, 'card') the rest, and the read panel heads with that AI read line.
thCaption(b) is unchanged for every other caller.

DRIVEN: the shipped thCaption / _thCaptionFull cut from tv/control_ui.html and run in node with its helpers stubbed; the
stage's and the panel's writers read from their own lines. RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
import js_strip  # noqa: E402  (one comment stripper for the laws)
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
STUBS = r"""
function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function thReaderBadge(){ return ''; } function thHandoffNote(){ return ''; } function thStallNote(){ return ''; }
function thSocketPill(){ return ''; } function _diabloScene(){ return null; } function thDossierLine(){ return ''; }
function thSeal(){ return ''; } function thReadStatus(){ return ''; } function _thKaiCaption(b){ return 'KAI ' + b.n; }
function thSupersededIntake(){ return null; }
var TH = { sessions: [{ t0: 1000 }], sn: 1, allBeats: [] };
"""


def _ui():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


def _function(src, name):
    head = "  function %s(" % name
    assert src.count(head) == 1, "PREMISE: %s is declared %d times" % (name, src.count(head))
    i = src.index(head)
    j = src.index("\n  }\n", i)
    return src[i:j + 4]


def _run(beats):
    if NODE is None:
        raise AssertionError("node is not installed on this PC - this law runs the shipped Theatre in node and does not skip")
    src = _ui()
    prog = (STUBS + "var _thCapIdent = null;\n" + _function(src, "thCaption") + _function(src, "_thCaptionFull") + r"""
var beats = JSON.parse(process.argv[2]), out = [];
beats.forEach(function(b){ out.push({ full: thCaption(b), bar: thCaption(b, 'bar'), card: thCaption(b, 'card') }); });
console.log(JSON.stringify(out));
""")
    d = tempfile.mkdtemp(prefix="theatre_bar_")
    try:
        h = os.path.join(d, "h.js")
        with io.open(h, "w", encoding="utf-8") as fh:
            fh.write(prog)
        r = subprocess.run([NODE, h, json.dumps(beats)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    finally:
        shutil.rmtree(d, True)          # the scratch-dir law pairs a mkdtemp with an rmtree
    assert r.returncode == 0, r.stderr[-800:]
    return json.loads(r.stdout.strip().splitlines()[-1])


READ = {"n": 7, "ts": 61000, "completedTs": 63500, "frameId": "f_0007", "frame": "reel_s_1/f_0007.jpg", "frameOk": True,
        "names": ["Shako"], "model": "deep", "stashTab": "personal"}
INTAKE = {"intakeBeat": True, "ts": 62000, "intake": {"ok": True, "total": 3, "counts": {"El": 3}, "tab": "runes"}}


class TheTheatreWearsOneCaptionBar(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.read, cls.intake = _run([READ, INTAKE])

    def test_baseline_the_whole_caption_still_carries_the_read_card(self):
        self.assertIn("read #7", self.read["full"])
        self.assertIn("th-airead", self.read["full"], "PREMISE: the read card is gone from thCaption - the case cannot distinguish")

    def test_a_read_beats_bar_is_its_identity_line_only(self):
        """* THE POINT - the bar over the film is one line; the AI read card is the panel's"""
        bar, card = self.read["bar"], self.read["card"]
        self.assertTrue(bar.startswith("read #7"), bar)
        self.assertNotIn("th-airead", bar, "the AI read card rides the caption bar again")
        self.assertNotIn("<br>", bar, "the bar breaks onto a second line")
        self.assertIn("th-airead", card)
        self.assertEqual(bar + card, self.read["full"], "the bar and the card are not the whole caption")

    def test_a_one_line_beat_is_all_bar(self):
        self.assertEqual(self.intake["bar"], self.intake["full"])
        self.assertEqual(self.intake["card"], "")

    def test_the_stage_writes_the_bar_and_the_panel_heads_with_the_read_line(self):
        code = js_strip.strip_js_comments(_ui())
        i = code.index("  function thPaint(){")
        paint = code[i:code.index("\n  }\n", i)]
        self.assertNotIn("$('th-caption').innerHTML", paint, "thPaint writes the full caption again")
        self.assertEqual(paint.count("thCaptionBar("), 6, "a beat branch no longer writes the one-line bar")
        self.assertNotIn("thCaption(lr2)", paint, "the standing read's card rides the footage bar again")
        self.assertIn("var _airead = String(thCaption(b, 'card') || '')", code, "the read panel no longer heads with the AI read line")
        self.assertIn(".th-caption .th-bar .th-bar-t { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
                      code, "the caption bar may wrap onto more lines again")
        self.assertIn(".th-caption .th-bar .th-bar-more { flex: none; }", code, "the read-card control can be cut by the ellipsis again")


RED_PROOF = [
    {"why": "#210 - the caption bar carries the whole AI read card again (it climbs over the film)",
     "file": "tv/control_ui.html",
     "find": "    if (part === 'bar') return _thCapIdent !== null ? _thCapIdent : full;\n",
     "replace": "    if (part === 'bar') return full;\n",
     "matches": 1},
    {"why": "#210 - a read beat writes its full caption over the film again",
     "file": "tv/control_ui.html",
     "find": "      thCaptionBar((_rpC ? _rpC + ' ' : '') + thCaption(b, 'bar'));",
     "replace": "      $('th-caption').innerHTML = (_rpC ? _rpC + ' ' : '') + thCaption(b) + _ffC;",
     "matches": 1},
    {"why": "#210 - the AI read line leaves the caption and the read panel never shows it",
     "file": "tv/control_ui.html",
     "find": "    var _airead = String(thCaption(b, 'card') || '').replace(/^(\\s*<br>)+/, '');\n",
     "replace": "    var _airead = '';\n",
     "matches": 1},
    {"why": "#210 - the caption bar may wrap again",
     "file": "tv/control_ui.html",
     "find": "  .th-caption .th-bar .th-bar-t { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }\n",
     "replace": "  .th-caption .th-bar .th-bar-t { min-width: 0; }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
