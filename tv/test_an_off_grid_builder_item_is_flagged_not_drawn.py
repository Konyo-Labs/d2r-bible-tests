# -*- coding: utf-8 -*-
"""ALT inject run 2026-10-24 (bugs 2 and 3) - A BUILDER ITEM PAST ITS GRID'S EDGE IS FLAGGED, NEVER DRAWN OFF-GRID OR LOST.

GrokBot's ALT edge batch stored:
  * bug 2: a 41st inventory item at x=10 - the inventory drew it OUTSIDE the 10x4 grid ("Nagelring at 11,1");
  * bug 3: a shared-stash item at x=9 w=2 - the Shared tab counted 1 and the grid drew nothing; only a quiet
    'does not fit this grid' note said so.
One rule now covers both, through ONE helper (_cbOffGridHtml): an item whose stored footprint leaves its grid is not
placed, and an alert under the grid names it with its stored spot and size (class cb-offgrid, data-offgrid = how many).
The tab that counts it says how many of its items are not drawn. The stored build is never rewritten (nothing is
refused or dropped: the user decides where it goes).

Whole page in node (tv/vault_page_node.py): the builder opens a seeded build, then its stash's Shared tab.
RED_PROOF: draw every inventory tile again, or drop the flag from _cbBagHtml, and this fails.
"""
import json
import os
import re
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
import vault_page_node as VPN  # noqa: E402


def _it(i, n, b, **k):
    d = {"id": i, "name": n, "q": "u", "base": b}
    d.update(k)
    return d


BUILD = {"name": "GBL-TEST-Edge", "cls": "Sorceress", "level": 90, "active": 0, "notes": "law", "from": None, "at": 1792800000002,
         "sets": [{"name": "Set 1", "ws": 1, "swap": {}, "slots": {},
                   "inv": [_it("u120", "Nagelring", "rin", x=0, y=0, w=1, h=1),
                           _it("u120", "Nagelring", "rin", x=10, y=0, w=1, h=1)]}],
         "stash": [],
         "shared": [_it("u285", "Herald of Zakarum", "pa9", x=9, y=0, w=2, h=4)]}

PRELUDE = r"""
Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });
location.protocol = 'file:'; location.href = 'file:///spec/bible.html'; location.origin = 'null'; location.host = ''; location.hostname = '';
localStorage.setItem('d2r_ownerClaim', '*');
localStorage.setItem('d2r_charBuilds', JSON.stringify({ gbltestedge: __BUILD__ }));
localStorage.setItem('d2r_cbSel', 'gbltestedge');
"""
BODY = r"""
H.flush(60, 3);
window.openCharBuilder('gbltestedge'); H.flush(60, 3);
OUT.win = (document.getElementById('cb-win') || {}).innerHTML || '';
window._cbOpenStash(); H.flush(60, 3); window._cbStashArea('shared'); H.flush(60, 3);
OUT.modal = (document.getElementById('cb-modal') || {}).innerHTML || '';
OUT.stored = window.LSR.getItem('d2r_charBuilds');
"""


class AnOffGridBuilderItemIsFlaggedNotDrawn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = VPN.run(BODY, prelude=PRELUDE.replace("__BUILD__", json.dumps(BUILD)), timeout=300)

    def test_the_inventory_draws_nothing_outside_its_grid(self):
        at = re.findall(r'class="cb-it[^"]*"[^>]*data-at="(\d+),(\d+),(\d+),(\d+)"', self.out["win"])
        self.assertTrue(at, "the inventory drew no tile at all")
        for x, y, w, h in at:
            self.assertTrue(int(x) + int(w) <= 10 and int(y) + int(h) <= 4,
                            "bug 2: an inventory tile is drawn at %s,%s (%sx%s), outside the 10x4 grid" % (x, y, w, h))

    def test_the_inventory_flags_the_off_grid_item(self):
        m = re.search(r'<div class="cb-note cb-offgrid"[^>]*data-offgrid="(\d+)"[^>]*>([^<]*)', self.out["win"])
        self.assertTrue(m, "bug 2: no off-grid flag under the inventory")
        self.assertEqual(m.group(1), "1")
        self.assertIn("Nagelring", m.group(2))

    def test_the_shared_stash_flags_the_off_grid_item(self):
        m = re.search(r'<div class="cb-note cb-offgrid"[^>]*data-offgrid="(\d+)"[^>]*>([^<]*)', self.out["modal"])
        self.assertTrue(m, "bug 3: the Shared tab counts the item but no off-grid flag says why it is not drawn")
        self.assertEqual(m.group(1), "1")
        self.assertIn("Herald of Zakarum", m.group(2))
        grid = self.out["modal"][self.out["modal"].index('class="cb-bag'):m.start()]
        self.assertNotIn("Herald of Zakarum", grid, "bug 3: the off-grid item is still drawn as a tile in the grid")

    def test_the_tab_that_counts_it_says_it_is_not_drawn(self):
        self.assertTrue(re.search(r'title="Shared of this build\.[^"]*1 not drawn', self.out["modal"]),
                        "bug 3: the Shared tab's count does not say one of its items is not drawn")

    def test_the_stored_build_is_not_rewritten(self):
        st = json.loads(self.out["stored"])["gbltestedge"]
        self.assertEqual(len(st["sets"][0]["inv"]), 2)
        self.assertEqual(len(st["shared"]), 1)

RED_PROOF = [
    {"why": "bug 2 - every inventory tile is drawn again, so a 41st item sits outside the 10x4 grid",
     "file": "bible.html",
     "find": "      if (_cbOutside(e, CB_INV_W, CB_INV_H)){ off.push(e); return; }   /* bug 2: flagged under the grid, never drawn outside it */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "bug 2 - the off-grid inventory item is skipped with no flag under the grid, so it is silently lost",
     "file": "bible.html",
     "find": "      + _cbOffGridHtml(off, CB_INV_W, CB_INV_H, 'inventory');\n",
     "replace": "      ;\n",
     "matches": 1, "needs": "node"},
    {"why": "bug 3 - the Shared tab counts the item and no flag under its grid says why it is not drawn",
     "file": "bible.html",
     "find": "      + _cbOffGridHtml(off, cols, rowsN, String(spec[2]).toLowerCase() + ' grid')\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "bug 3 - the tab that counts the item never says one of its items is not drawn",
     "file": "bible.html",
     "find": "          + (offN ? ' ' + offN + ' not drawn: outside the grid.' : '') };\n",
     "replace": "          + '' };\n",
     "matches": 1, "needs": "node"},
    {"why": "only the corner is tested, so an item whose footprint runs past the edge (x=9, w=2) is not flagged",
     "file": "bible.html",
     "find": "    return x < 0 || y < 0 || x + w > cols || y + h > rows;\n",
     "replace": "    return x < 0 || y < 0 || x >= cols || y >= rows;\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
