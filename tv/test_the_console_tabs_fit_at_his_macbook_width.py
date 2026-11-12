# -*- coding: utf-8 -*-
"""v3901 (REG-3765) - THE CONSOLE'S TABS FIT ON ONE ROW AT HIS MACBOOK'S 1512 px.

GrokBot (#230, 11-12, his live console at 1512): "the TV·D tab wraps alone onto a second tab row". MEASURED here with a
headless sweep (4 px steps, one scratch console): with the 1700 px step's tab padding (7px 8px) the strip wraps TV·D onto
its own full-width row from 1504 to 1544 px and fits from 1548 up; the tighter step (padding 7px 6px, gap 3px) entered only
at 1500 - and the render gate's widths (1440 / 1280 / 1120 / 901) never landed in the band, so it shipped green. The step
now enters at 1600: the band plus ~50 px, because his console renders in WebKit, whose type can measure wider than
headless Chrome's. Re-swept with the fix: 1500-1640 all one row; the Grok CLI read 2 rows before and 1 after, cold.

A font-metric band cannot be a render assertion that holds on every machine (visual-regression-detector 4b: the geometry
gate is a floor and the parse is the proof), so this law reads the stylesheet: the step that tightens the tabs must start at
or above the measured band's end plus that margin.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

#: measured 11-12 (headless Chrome, 4 px steps): the 1700 step's strip fits only from here up
BAND_END_PX = 1548
#: room for his console's WebKit type, which measures wider than headless Chrome's
WEBKIT_MARGIN_PX = 40


def _tighten_step(css):
    """-> the max-width (px) of the media query whose rules give the tabs their tightest padding (7px 6px), or None."""
    for m in re.finditer(r"@media \(max-width: (\d+)px\) \{(.*?)\n  \}", css, re.S):
        body = m.group(2)
        if ".head-tabs { gap: 3px; }" in body and "padding: 7px 6px;" in body:
            return int(m.group(1))
    return None


class TheConsoleTabsFitAtHisMacbookWidth(unittest.TestCase):

    def setUp(self):
        with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
            self.css = fh.read()

    def test_the_tightening_step_covers_the_measured_band(self):
        """* THE POINT - GrokBot 11-12 at 1512: TV·D alone on a second row; the band was 1504-1544"""
        w = _tighten_step(self.css)
        self.assertIsNotNone(w, "PREMISE: the step that tightens the tabs (7px 6px, gap 3px) is no longer in the stylesheet")
        self.assertGreaterEqual(w, BAND_END_PX + WEBKIT_MARGIN_PX,
                                "the tabs tighten only at %dpx, inside the band that wraps TV·D (1504-1544 measured)" % w)

    def test_his_macbook_width_is_inside_the_step(self):
        self.assertGreaterEqual(_tighten_step(self.css), 1512)


RED_PROOF = [
    {"why": "REG-3765 - the tabs tighten only at 1500 again: TV·D wraps alone at his MacBook's 1512",
     "file": "tv/control_ui.html",
     "find": "  @media (max-width: 1600px) {\n    .head-tabs { gap: 3px; }\n",
     "replace": "  @media (max-width: 1500px) {\n    .head-tabs { gap: 3px; }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
