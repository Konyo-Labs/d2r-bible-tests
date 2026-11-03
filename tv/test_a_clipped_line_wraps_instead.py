# -*- coding: utf-8 -*-
"""LAW (v3859): a line he acts on wraps, it is never shaved. The Today stat row ('0 runs recorded today ·
0 tallies synced') at 375 and the zone why-line ('the way into the Andariel run') at 901 were ellipsised by
the render probe. Both may take a second line. Red-proof: on bb358e0e neither rule exists and the page
target clips 2 at 375 / 1 at 901 against floors of 1 / 0."""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
SRC = open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()


class TheLaw(unittest.TestCase):
    def test_the_today_stat_row_wraps(self):
        self.assertIn(".tf-row.tf-stat .tf-t { white-space: normal; overflow: visible; text-overflow: clip; }", SRC)

    def test_the_zone_why_line_wraps_after_the_ellipsis_rule(self):
        a = SRC.index(".tzz-txt em, .tzz-txt i { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }")
        b = SRC.index(".tzz-txt em.tzz-why { white-space: normal; overflow: visible; text-overflow: clip; }")
        self.assertLess(a, b)


if __name__ == "__main__":
    unittest.main()
