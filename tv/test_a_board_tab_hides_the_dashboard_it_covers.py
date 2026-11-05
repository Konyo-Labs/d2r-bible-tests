# -*- coding: utf-8 -*-
"""v3864 (GrokBot Batch A 2, #230 6656116697) - WHAT CANNOT BE PRESSED IS NOT SHOWN.

GrokBot, v3860 at 1440x1000: with a board tab open (Runewords), the console's home dashboard painted through under the board.
`body.shell-open .shell > :not(.topbar){pointer-events:none}` made it dead on purpose (no click may leak through the board's
semi-transparent edges), so #chron-scan, #chron-run and the vault twins looked live and did nothing. Now #home-dash is
opacity 0 while a board tab is open - opacity, not visibility, because that rule keeps the console subtree in the layout
tree on purpose. RED_PROOF below.
"""
import io
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class ABoardTabHidesTheDashboardItCovers(unittest.TestCase):

    def test_the_dead_dashboard_is_not_painted_under_a_board(self):
        s = io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8").read()
        self.assertIn('id="home-dash"', s, "PREMISE: the home dashboard is gone")
        self.assertIn("body.shell-open .shell > :not(.topbar) {\n  pointer-events: none;\n}", s,
                      "PREMISE: the board no longer makes the console dead underneath it")
        self.assertRegex(s, r"body\.shell-open #home-dash \{\n  opacity: 0;\n\}",
                         "the dead dashboard still paints under an open board tab")
        self.assertIsNone(re.search(r"body\.shell-open #home-dash \{[^}]*visibility:\s*hidden", s),
                          "the dashboard left the layout tree (visibility), against the shell rule's own note")


RED_PROOF = [
    {"why": "v3864 - the dead home dashboard paints under an open board tab again",
     "file": "tv/control_ui.html",
     "find": "body.shell-open #home-dash {\n  opacity: 0;\n}\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
