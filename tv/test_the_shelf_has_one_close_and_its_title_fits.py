# -*- coding: utf-8 -*-
"""v3864 (GrokBot Batch A 1 and 5, #230 6656116697) - THE SHELF HAS ONE CLOSE, AND THE THEATRE'S TITLE IS READ WHOLE.

Batch A (v3860, five window sizes): opening the SHELF drew two close buttons on one line - the shelf's own ✕ (#th-shelf-x)
and the theatre's "✕ CLOSE" (#th-close), top ~141 at 1024 - two exits for one job, the d2jsp picker's old bug. And the
theatre title "🎞 THE THEATRE · EYES ON HISTORY" rendered 122px of its 383 at 1024, 1440 and 1920: REG-2134 had given it a
flex-basis of 0, so it got a third of the spare room. Now the theatre's close is display:none while the shelf is open (the
same rule that already hides the strip's controls), and the title takes its own width first, giving way only when the row
truly lacks room (one line, an ellipsis when narrow - REG-2134 kept). A source law: the render gate on CI and GrokBot's live
look measure the pixels. RED_PROOF below.
"""
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
UI = os.path.join(HERE, "control_ui.html")


def ui():
    return io.open(UI, encoding="utf-8").read()


class TheShelfHasOneClose(unittest.TestCase):

    def test_the_theatres_close_hides_while_the_shelf_is_open(self):
        s = ui()
        self.assertIn('id="th-close"', s, "PREMISE: the theatre's close is gone")
        self.assertIn('id="th-shelf-x"', s, "PREMISE: the shelf's own close is gone")
        self.assertRegex(s, r"body:has\(#th-shelfov:not\(\[hidden\]\)\) #th-close \{ display: none !important; \}",
                         "the theatre's ✕ CLOSE still stands beside the shelf's ✕")

    def test_the_title_takes_its_own_width_first(self):
        s = ui()
        m = re.search(r"  \.th-topline \.th-tag \{([^}]*)\}", s)
        self.assertIsNotNone(m, "PREMISE: the topline title rule is gone")
        rule = m.group(1)
        self.assertIn("flex: 0 1 auto", rule, "the title gets a share of the spare room again (122px of 383 at 1024)")
        self.assertIn("white-space: nowrap", rule, "REG-2134: the title may wrap into a column again")
        self.assertIn("text-overflow: ellipsis", rule, "REG-2134: a narrow window no longer ends the title in an ellipsis")


RED_PROOF = [
    {"why": "v3864 - the shelf shows two close buttons again",
     "file": "tv/control_ui.html",
     "find": "  body:has(#th-shelfov:not([hidden])) #th-close { display: none !important; }\n",
     "replace": "",
     "matches": 1},
    {"why": "v3864 - the theatre title gets a third of the spare room again and is cut to 122px",
     "file": "tv/control_ui.html",
     "find": "text-overflow: ellipsis; min-width: 0; flex: 0 1 auto; }",
     "replace": "text-overflow: ellipsis; min-width: 0; flex: 1 1 0; }",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
