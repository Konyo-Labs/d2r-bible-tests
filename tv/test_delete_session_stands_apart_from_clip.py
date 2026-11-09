# -*- coding: utf-8 -*-
"""v3890 (#186) - THE THEATRE'S "... more" MENU KEEPS "Delete session" APART FROM "Clip".

GrokBot #230 (11-09, the Shelf trap hunt): "the '... more' menu has Delete session right next to Clip ... easy to hit by
mistake". It still asks twice, but it sat flush under Clip in the same gold. Now the one destructive item carries
.th-danger: a gap and a rule above it and the danger colour. RENDERED 11-09 on a private console at 1120: Clip ends at
y=425, Delete starts at 441 with the red rule between, its text rgb(255, 85, 85) beside the menu's gold. RED_PROOF below.
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
import js_strip  # noqa: E402


def _ui():
    with io.open(os.path.join(HERE, "control_ui.html"), encoding="utf-8") as fh:
        return fh.read()


class DeleteSessionStandsApartFromClip(unittest.TestCase):

    def test_delete_is_the_danger_item_and_the_last_one(self):
        ui = _ui()
        i = ui.index('<div id="th-more-pop" hidden>')
        pop = ui[i:ui.index("</div>", i)]
        ids = re.findall(r'<button class="th-btn[^"]*" id="([a-z-]+)"', pop)
        self.assertEqual(ids[-1], "th-del", "Delete session is no longer the menu's last item: %s" % ids)
        self.assertIn('<button class="th-btn th-danger" id="th-del"', pop)
        self.assertEqual(pop.count("th-danger"), 1, "a second item wears the danger style")

    def test_the_danger_item_has_its_gap_rule_and_colour(self):
        css = js_strip.strip_js_comments(_ui())
        m = re.search(r"#th-more-pop \.th-btn\.th-danger \{([^}]*)\}", css)
        self.assertTrue(m, "the danger item has no style of its own")
        self.assertIn("margin-top: 12px", m.group(1))
        self.assertIn("color: var(--acc-danger, #ff5555)", m.group(1))
        self.assertIn("#th-more-pop .th-btn.th-danger::before { content: \"\"; position: absolute;", css,
                      "the rule above Delete is gone")


RED_PROOF = [
    {"why": "v3890 (#186) - Delete session sits flush under Clip in the menu's gold again",
     "file": "tv/control_ui.html",
     "find": '<button class="th-btn th-danger" id="th-del"',
     "replace": '<button class="th-btn" id="th-del"',
     "matches": 1},
    {"why": "v3890 (#186) - the gap above Delete is gone",
     "file": "tv/control_ui.html",
     "find": "  #th-more-pop .th-btn.th-danger { margin-top: 12px;",
     "replace": "  #th-more-pop .th-btn.th-danger { margin-top: 0;",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
