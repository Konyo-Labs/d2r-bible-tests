# -*- coding: utf-8 -*-
"""v3849 — a fleet hover card does not cover the console column.

The card is position:absolute; right:0 and grows left. On a wide card that left edge crosses out of
the fleet rail and over the console column. _fttRailClamp(cardLeft, cardRight, railLeft) returns a
left edge that is never left of the rail and never past the card's right edge. The hover clears a
previous clamp, measures, and when the edge moved right sets minWidth 0 and maxWidth to the room
that remains inside the rail.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

UI = os.path.join(HERE, "control_ui.html")
FN = ("  function _fttRailClamp(cardLeft, cardRight, railLeft){\n", "\n  }\n")


def _src():
    with open(UI, encoding="utf-8") as f:
        return f.read()


def _clamp(cases):
    if not NODE:
        raise AssertionError("node is not on this machine - this gate does not skip")
    s = _src()
    start, end = FN
    if s.count(start) != 1:
        raise AssertionError("_fttRailClamp's anchor matched %d times" % s.count(start))
    i = s.index(start)
    fn = s[i:s.index(end, i) + len(end)]
    if fn.count("{") != fn.count("}"):
        raise AssertionError("the cut is not a whole function")
    js = "%s\nconsole.log(JSON.stringify(%s.map(function (c) { return _fttRailClamp(c[0], c[1], c[2]); })));\n" % (
        fn, json.dumps(cases))
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the cut function did not run in node: %s" % r.stderr[-400:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class TestFleetCardNeverCoversConsoleColumn(unittest.TestCase):
    def test_the_left_edge_stays_on_the_rail_and_never_passes_the_right_edge(self):
        got = _clamp([
            [120, 400, 100],
            [40, 300, 100],
            [10, 40, 100],
            [100, 200, 100],
            [-20, 50, 0],
            [50, 10, 0],
            [None, None, None],
        ])
        self.assertEqual(got, [120, 100, 40, 100, 0, 50, 0])

    def test_the_hover_clamps_to_the_rail_after_it_clears_a_previous_width(self):
        s = _src()
        i = s.index("document.addEventListener('pointerover'")
        hover = s[i:s.index("}, true);", i)]
        self.assertEqual(hover.count("_fttRailClamp("), 1)
        self.assertEqual(s.count("window._fttRailClamp = _fttRailClamp"), 1)
        self.assertLess(hover.index("card.style.maxWidth = ''"), hover.index("card.getBoundingClientRect()"))
        self.assertLess(hover.index("card.style.minWidth = ''"), hover.index("_fttRailClamp("))
        self.assertIn("row.closest('aside.rail')", hover)
        self.assertIn("card.style.minWidth = '0px'", hover)
        self.assertIn("card.style.maxWidth = (box.right - edge) + 'px'", hover)
        self.assertLess(hover.index("_fttRailClamp("), hover.index("card.style.maxWidth = (box.right - edge) + 'px'"))

    def test_the_red_proof_finds_match_once(self):
        for proof in RED_PROOF:
            with open(os.path.join(ROOT, proof["file"]), encoding="utf-8") as fh:
                body = fh.read()
            self.assertEqual(body.count(proof["find"]), proof["matches"], proof["why"])
            self.assertNotEqual(proof["find"], proof["replace"])


RED_PROOF = [
    {"why": "the card's left edge is left alone, so a wide card still covers the console column",
     "file": "tv/control_ui.html",
     "find": "    return edge;\n",
     "replace": "    return left;\n",
     "matches": 1},
    {"why": "the hover never asks the clamp, so the pure function does not move a real card",
     "file": "tv/control_ui.html",
     "find": "        var edge = _fttRailClamp(box.left, box.right, railLeft);\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
