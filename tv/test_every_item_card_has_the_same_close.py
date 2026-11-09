# -*- coding: utf-8 -*-
"""v3891 (#191, REG-3529) - EVERY ITEM CARD USES THE SAME CLOSE CONTROL.

His rule: every popup uses the same close. MEASURED: a material/rune/set-piece card already carries
`gic-close-btn` ("✕ close", title "press ESC"); the bosses-tab unique card (`renderItemDetailCard`)
had that button on its full path but the "item not found" and "no viable sources" returns had none;
the calc unique card (`renderAidCard` with context 'calc', what `navigateToItem` paints) had owned /
glossary / jump buttons and no close at all. Those paths now carry the same `gic-close-btn` the other
cards already use. RED_PROOF below.
"""
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()

PAGE = os.path.join(ROOT, "bible.html")


def _page():
    with io.open(PAGE, encoding="utf-8") as fh:
        return fh.read()


def _fn_from(src, head):
    i = src.index(head)
    start = src.index("{", i)
    depth = 0
    for k in range(start, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    raise AssertionError("%s was not closed" % head)


class EveryItemCardHasTheSameClose(unittest.TestCase):

    def test_the_unique_panel_close_is_on_every_path(self):
        body = _fn_from(_page(), "function renderItemDetailCard(itemName)")
        self.assertEqual(body.count('class="gic-close-btn" onclick="closeItemDetail()"'), 3,
                         "a renderItemDetailCard path no longer uses the shared close control")
        self.assertIn("item not found", body)
        i = body.index("item not found")
        self.assertIn("gic-close-btn", body[max(0, i - 220):i + 40],
                      "the 'item not found' card has no close")
        self.assertIn("No viable sources at current MF/level constraints.", body)
        j = body.index("No viable sources at current MF/level constraints.")
        self.assertIn("gic-close-btn", body[max(0, j - 280):j],
                      "the 'no viable sources' card has no close")

    def test_the_calc_unique_card_has_the_same_close(self):
        body = _fn_from(_page(), "function renderAidCard(name, opts)")
        self.assertIn(
            "${opts.context==='calc' ? `<button class=\"gic-close-btn\" onclick=\"window.closeDrop&&window.closeDrop();if(typeof clearActiveItem==='function')clearActiveItem()\" title=\"press ESC\">",
            body,
            "the calc unique card (navigateToItem / renderDetail) has no shared close control")


RED_PROOF = [
    {"why": "v3891 (#191, REG-3529) - the calc unique card has no close again",
     "file": "bible.html",
     "find": "        ${opts.context==='calc' ? `<button class=\"gic-close-btn\" onclick=\"window.closeDrop&&window.closeDrop();if(typeof clearActiveItem==='function')clearActiveItem()\" title=\"press ESC\">\u2715 close</button>` : ''}\n",
     "replace": "",
     "matches": 1},
    {"why": "v3891 (#191, REG-3529) - the 'item not found' card has no close again",
     "file": "bible.html",
     "find": "  if (!item) { panel.innerHTML = '<div class=\"gic-card\"><div style=\"display:flex;justify-content:flex-end\"><button class=\"gic-close-btn\" onclick=\"closeItemDetail()\" title=\"press ESC\">\u2715 close</button></div>item not found</div>'; return; }\n",
     "replace": "  if (!item) { panel.innerHTML = '<div class=\"gic-card\">item not found</div>'; return; }\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
