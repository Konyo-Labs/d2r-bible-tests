# -*- coding: utf-8 -*-
"""v3891 (#186, REG-3532) - THE SHELF OPENS AT REAL SIZE EVEN WHEN THE THEATRE IS HIDDEN.

`#th-shelfov` lived inside `#theatre`. `#theatre` is `display:none` while shut, and a
`position:absolute` (or even `position:fixed`) child of a `display:none` ancestor has a 0x0 box.
v3890 #186 put the theatre layer back before refusing (`_shelfRestoreLayer`) and still SAW a 0x0
after a chapter / theatre path. The overlay now sits next to `#th-dossier-ov` (a sibling of
`#theatre`, outside `.shell`) and is `position:fixed` with a z-index above cinema (900) and
shadow-theatre (976), so SHELF always has a viewport box. `_shelfRestoreLayer` stays. RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

UI = os.path.join(HERE, "control_ui.html")


def _ui():
    with io.open(UI, encoding="utf-8") as fh:
        return fh.read()


class TheShelfOpensAtRealSize(unittest.TestCase):

    def test_the_overlay_is_a_sibling_of_the_theatre_not_a_child(self):
        src = _ui()
        self.assertEqual(src.count('id="th-shelfov"'), 1, "the shelf overlay was doubled or removed")
        self.assertIn('<div id="th-shelfov" hidden></div>\n  <div id="th-dossier-ov" hidden></div>', src,
                      "the shelf overlay is not sitting next to the dossier (outside #theatre)")
        th = src.index('<div class="theatre" id="theatre"')
        # the next major sibling overlays start at #th-dossier-ov; the shelf must not appear before theatre closes
        inner = src[th:src.index('<div id="th-shelfov" hidden></div>')]
        self.assertNotIn('id="th-shelfov"', inner,
                         "the shelf overlay is still a child of #theatre, so it opens 0x0 when the theatre is hidden")

    def test_the_overlay_is_fixed_above_the_theatre(self):
        src = _ui()
        i = src.index("#th-shelfov {")
        block = src[i:src.index("}", i) + 1]
        self.assertIn("position: fixed", block,
                      "the shelf overlay is not position:fixed, so its box still depends on a parent")
        self.assertIn("z-index: 978", block,
                      "the shelf overlay sits under cinema (900) or shadow-theatre (976)")


RED_PROOF = [
    {"why": "v3891 (#186, REG-3532) - the shelf overlay is position:absolute again, so its box depends on a parent",
     "file": "tv/control_ui.html",
     "find": "  #th-shelfov { position: fixed;",
     "replace": "  #th-shelfov { position: absolute;",
     "matches": 1},
    {"why": "v3891 (#186, REG-3532) - the shelf overlay is no longer a sibling of the dossier (back inside a hidden parent)",
     "file": "tv/control_ui.html",
     "find": "  <div id=\"th-shelfov\" hidden></div>\n  <div id=\"th-dossier-ov\" hidden></div>\n",
     "replace": "  <div id=\"th-dossier-ov\" hidden></div>\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
