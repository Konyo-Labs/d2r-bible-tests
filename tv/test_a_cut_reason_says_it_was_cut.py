# -*- coding: utf-8 -*-
"""v3880 (REG-3375, GrokBot #6707144313 on his live State panel) - A REASON CUT TO FIT SAYS IT WAS CUT.

GrokBot quoted his Shadow-gate row: "On 152 of the 735 item names the reader has ever scored, the console ticked the item by
itself where a stricter rule would have asked you first - never the other way round. Stricter means fewer automatic ticks and
more items waiting for you to confirm. Nothing · your choices: Keep it as it is · ..." - the ask row sliced its reason at 260
characters, and "Nothing" was the first word of a sentence the slice cut off, with nothing saying so.

The law drives the panel's own _vxClip (cut from tv/control_ui.html) and the ask row's use of it: a reason that fits is
untouched; a long one ends at its last sentence when one is near the limit, else at a word with an ellipsis; never a
dangling first word. RED_PROOF below.
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
NODE = shutil.which("node") or shutil.which("nodejs")
UI = os.path.join(HERE, "control_ui.html")
START = "  function _vxClip(s, n){"

SHADOW = ("On 152 of the 735 item names the reader has ever scored, the console ticked the item by itself where a "
          "stricter rule would have asked you first - never the other way round. Stricter means fewer automatic ticks "
          "and more items waiting for you to confirm. Nothing changes until you choose, and the choice can be undone.")


def _clip(cases):
    src = io.open(UI, encoding="utf-8").read()
    if src.count(START) != 1:
        raise AssertionError("_vxClip moved - re-point this law")
    i = src.index(START)
    fn = src[i:src.index("\n  }\n", i) + 4]
    js = ("var window = {};\n" + fn + "\nprocess.stdout.write(JSON.stringify("
          + json.dumps(cases) + ".map(function (c) { return _vxClip(c[0], c[1]); })));")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60, encoding="utf-8")
    if r.returncode != 0:
        raise AssertionError(r.stderr[-600:])
    return json.loads(r.stdout)


@unittest.skipUnless(NODE, "node is required to drive the panel's own _vxClip - UNMEASURED here, not a pass")
class ACutReasonSaysItWasCut(unittest.TestCase):

    def test_his_shadow_gate_reason_ends_at_a_sentence_not_on_a_dangling_word(self):
        """* THE POINT: the row GrokBot read ended "...to confirm. Nothing"""
        out = _clip([[SHADOW, 260]])[0]
        self.assertTrue(out.endswith("waiting for you to confirm."), out[-80:])
        self.assertNotIn("Nothing", out)

    def test_no_sentence_near_the_limit_cuts_at_a_word_with_an_ellipsis(self):
        long_word_run = "word " * 80
        out = _clip([[long_word_run, 100]])[0]
        self.assertTrue(out.endswith(u"\u2026"), out[-20:])
        self.assertLessEqual(len(out), 101)
        self.assertTrue(out[:-1].endswith("word"), "it cut inside a word")

    def test_a_reason_that_fits_is_untouched_and_unknown_is_empty(self):
        self.assertEqual(_clip([["short reason.", 260], [None, 260]]), ["short reason.", ""])

    def test_the_ask_row_uses_it(self):
        src = io.open(UI, encoding="utf-8").read()
        self.assertIn("+ esc(_vxClip(a.why || r.why, 260))", src)
        self.assertNotIn("String(a.why || r.why || '').slice(0, 260)", src)


RED_PROOF = [
    {"why": "REG-3375 - the ask row slices its reason mid-sentence again ('...to confirm. Nothing')",
     "file": "tv/control_ui.html",
     "find": "    if (dot >= Math.floor(n * 0.6)) return c.slice(0, dot + 1);\n    return c.replace(/\\s+\\S*$/, '') + '\\u2026';\n",
     "replace": "    return c;\n", "matches": 1},
    {"why": "REG-3375 - the ask row stops using the clip",
     "file": "tv/control_ui.html",
     "find": "         + esc(_vxClip(a.why || r.why, 260))",
     "replace": "         + esc(String(a.why || r.why || '').slice(0, 260))", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
