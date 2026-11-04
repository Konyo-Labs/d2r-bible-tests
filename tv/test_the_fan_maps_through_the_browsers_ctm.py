# -*- coding: utf-8 -*-
"""v3861 - THE FAN SOLVER MAPS CLIENT PIXELS THROUGH THE SVG'S OWN SCREEN CTM, NOT THROUGH ITS BOX.

`_hrtFanFit` turned every label's client rect into fan units with `scale = sr.width / 960` and the box's
left/top as origin. That was exact while the svg was width-sized (v2745). v3178 capped its height
(`max-height: calc(86vh - 150px)`), so on a wide window `preserveAspectRatio` meet scales the fan by HEIGHT and
letterboxes it. MEASURED 2026-11-04 on the Konyo · ALT (viewBox 960x780), `svg.getScreenCTM()` against the box:

    window      box scale   CTM scale (a)   CTM origin x   box origin x
    1440x1000   1.359       0.910           276            60       -> labels mapped 1.49x too far apart
    1120x1000   1.046       0.910           116            51
     901x1000   0.831       0.831            44            44       -> exact only where width-bound

So at 1440 the solver moved a stack, scored `collisions: 0`, and the pixels still overlapped 10x8 px: in its
model 18 units were 24.5 px, on screen 16.4 px. The map is now the browser's own CTM, letterbox included; a
stub with no CTM keeps the box map, and every report says which one it used (`scaleFrom`).

⚠ THIS LAW EXECUTES THE REAL FUNCTION over the stub DOM of test_the_fan_names_the_stacks_it_kept, with the
1440x1000 geometry above. It pins the joint (which map was used), not a pixel; the pixels were measured
separately on the rendered console. [[the-unjoined-end]]
"""
import os
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

import test_the_fan_names_the_stacks_it_kept as STACKS  # noqa: E402

_LETTERBOX = """
const _svg = root.querySelector('svg.hrt');
_svg.getBoundingClientRect = () => ({ left: 60, top: 0, right: 1365, bottom: 710, width: 1305, height: 710 });
_svg.getScreenCTM = () => ({ a: 0.910, b: 0, c: 0, d: 0.910, e: 276, f: 0 });
"""
_NO_CTM = """
const _svg = root.querySelector('svg.hrt');
_svg.getBoundingClientRect = () => ({ left: 60, top: 0, right: 1365, bottom: 710, width: 1305, height: 710 });
"""


@unittest.skipIf(shutil.which("node") is None, "node is absent - UNMEASURED, not passing")
class TheFanMapsThroughTheBrowsersCtm(unittest.TestCase):

    def test_a_letterboxed_fan_is_measured_at_the_scale_it_was_drawn_at(self):
        ff, _dom = STACKS._run(self, STACKS._SPEC_PARTIAL + _LETTERBOX)
        self.assertEqual(ff.get("scaleFrom"), "ctm", "the solver ignored the svg's own CTM: %r" % (ff,))
        self.assertAlmostEqual(ff.get("scale"), 0.91, places=3,
                               msg="the fan was measured at %r, the browser drew it at 0.910 - every label sits "
                                   "1.49x too far from its neighbour in the solver's model" % ff.get("scale"))
        self.assertAlmostEqual(ff.get("boxScale"), 1.3594, places=3,
                               msg="PREMISE: the box map this fixture must tell apart from the CTM is not 1.359")

    def test_a_fan_with_no_ctm_keeps_the_box_map_and_says_so(self):
        ff, _dom = STACKS._run(self, STACKS._SPEC_PARTIAL + _NO_CTM)
        self.assertEqual(ff.get("scaleFrom"), "box")
        self.assertAlmostEqual(ff.get("scale"), 1.3594, places=3)


RED_PROOF = [
    {"why": "v3861 - the solver measures a letterboxed fan through its box again (sr.width / 960): at 1440x1000 it "
            "solved 1.49x too wide and scored collisions 0 over a 10x8 px overlap",
     "file": "tv/control_ui.html",
     "find": "    var _ctm = !!(_M && _M.a > 0.05);\n",
     "replace": "    var _ctm = false;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
