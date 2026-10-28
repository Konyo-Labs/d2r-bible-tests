# -*- coding: utf-8 -*-
"""REG-2878 (#83, his design: "a listed copy still counts in its spot") - A LISTED COPY WEARS A SMALL MARK EVERYWHERE IT DRAWS.

MEASURED before (whole page, node): nothing on the card, the window, FIND or the MOVE row could say a copy is listed on
d2jsp. The listing lived in the D2JSP tab's own stores, and no copy carried it.

Now every surface that draws a copy reads the copy record's trade slot (REG-2877) through one reader
(window._vaultTradeOf, read once per store text):
  - the MOVE row of that copy wears "listed";
  - FIND says "listed", or "N listed", beside the name;
  - in the mule window, the tile of that copy (its key names its copyIx, REG-2876) wears an "L" mark, and its label says
    so;
  - on the shelf card, the cell of that copy wears "listed".
The copy still counts in its spot: the count and the card's cells do not change. Only the listed copy wears the mark.
Whole page in node, never a browser. RED_PROOF below.
"""
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
BODY = r"""
var W = window, GULL = 'Gull (dagger)';
function paint(){ W.renderVault(); H.flush(60, 3); }
function shelfCells(){ var s = (document.getElementById('vault-shelf') || {}).innerHTML || '';
  return (s.match(/<div class="vm-cell[^"]*"[^>]*data-vault-item="Gull \(dagger\)"[\s\S]*?<\/button><\/div>/g) || []); }
function moveRows(){ var h = (document.getElementById('vault-move-list') || {}).innerHTML || '';
  return (h.match(/<li class="vmv-row[^>]*>[\s\S]*?<\/li>/g) || []).filter(function(x){ return x.indexOf('data-name="' + GULL + '"') >= 0; })
    .map(function(x){ return { ci: +((x.match(/data-copy="(\d+)"/) || [])[1]), listed: x.indexOf('data-trade="listed"') >= 0 }; }); }
function tiles(){ W.openMuleCard('uni-weap'); var h = (document.getElementById('vault-detail') || {}).innerHTML || '';
  var out = {}, re = /<div class="vd-item([^"]*)"[^>]*data-key="(Gull \(dagger\)[^"]*)"[^>]*>([\s\S]*?)<\/div>/g, m;
  while ((m = re.exec(h))) out[m[2]] = { cls: m[1], mark: m[3].indexOf('vd-listed-mark') >= 0 };
  if (W.vaultCloseCard) W.vaultCloseCard(true); return out; }
function find(){ W.vaultFind('gull'); H.flush(400, 3); return (document.getElementById('vault-find-results') || {}).innerHTML || ''; }
W._vaultAutoIntakeSet(false);
['Gull', 'Gull'].forEach(function(n){ W.vaultHandAdd(n); });
W.vaultAssign(GULL, 'uni-weap'); paint();
OUT.before = { count: copyCount(GULL), cells: shelfCells().length, rows: moveRows(), tiles: tiles(), find: find() };
OUT.ev = W._vaultTradeEvent({ kind: 'listed', name: GULL, copyIx: 1, at: '2026-10-28T20:00:00Z' }); paint();
var sc = shelfCells();
OUT.after = { count: copyCount(GULL), cells: sc.length, listedCells: sc.map(function(c){ return c.indexOf('vm-cell-listed') >= 0; }),
              rows: moveRows(), tiles: tiles(), find: find() };
W._vaultTradeEvent({ kind: 'listed', name: GULL, copyIx: 0 }); paint();
OUT.both = find();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AListedCopyWearsItsMarkWhereItDraws(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=CLAIM, timeout=600)

    def test_premise_two_copies_drawn_and_nothing_marked(self):
        o = self.o
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertTrue(o["ev"]["ok"], o["ev"])
        b = o["before"]
        self.assertEqual(b["count"], 2)
        self.assertEqual(b["cells"], 2, "PREMISE: the shelf card does not draw both copies: %r" % b["cells"])
        self.assertEqual(sorted(b["tiles"]), ["Gull (dagger)", "Gull (dagger) #2"], "PREMISE: %r" % b["tiles"])
        self.assertFalse(any(t["mark"] for t in b["tiles"].values()))
        self.assertNotIn("vfr-listed", b["find"])

    def test_the_move_row_of_that_copy_says_listed(self):
        rows = dict((r["ci"], r["listed"]) for r in self.o["after"]["rows"])
        self.assertEqual(rows.get(1), True, "copy 1's MOVE row does not say listed: %r" % rows)
        self.assertEqual(rows.get(0), False, "copy 0's MOVE row says listed: %r" % rows)

    def test_find_says_how_many_copies_are_listed(self):
        self.assertRegex(self.o["after"]["find"], r'<span class="vfr-listed" data-trade="listed" title="[^"]*">listed</span>')
        self.assertIn('data-trade="listed" title="', self.o["both"])
        self.assertIn(">2 listed</span>", self.o["both"])

    def test_the_window_tile_of_that_copy_wears_the_mark(self):
        t = self.o["after"]["tiles"]
        self.assertTrue(t["Gull (dagger) #2"]["mark"] and "vd-listed" in t["Gull (dagger) #2"]["cls"], t)
        self.assertFalse(t["Gull (dagger)"]["mark"], "copy 0's tile wears the mark: %r" % t)

    def test_the_shelf_card_marks_one_cell_and_the_copy_still_counts(self):
        a = self.o["after"]
        self.assertEqual((a["count"], a["cells"]), (2, 2), "listing changed the count: %r" % a)
        self.assertEqual(a["listedCells"].count(True), 1, "not exactly one shelf cell marked: %r" % a["listedCells"])


RED_PROOF = [
    {"why": "REG-2878 - the MOVE row does not mark a listed copy",
     "file": "bible.html",
     "find": "            return '<b class=\"vmv-l1 vmv-listed\" data-trade=\"listed\" title=\"' + esc(window._vaultListedSay(x)) + '\">listed</b>'; }).join('') : '')",
     "replace": "            return ''; }).join('') : '')",
     "matches": 1, "needs": "node"},
    {"why": "REG-2878 - FIND does not say a copy is listed",
     "file": "bible.html",
     "find": "+'>'+esc(n)+'</span>'+_vfrTrade(n)+'<span class=\"vfr-loc\">'",
     "replace": "+'>'+esc(n)+'</span>'+'<span class=\"vfr-loc\">'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2878 - the window tile wears no mark",
     "file": "bible.html",
     "find": "        + (_lst ? '<span class=\"vd-listed-mark\" data-trade=\"listed\" aria-hidden=\"true\">L</span>' : '')   /* REG-2878 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2878 - every copy of a listed name wears the mark (not the copy its key names)",
     "file": "bible.html",
     "find": "        _lst = window._vaultTradeOf(p.n).filter(function(x){ return x.ci === _kci && x.state === 'listed'; })[0] || null; } } catch (eLs) { _lst = null; }",
     "replace": "        _lst = window._vaultTradeOf(p.n).filter(function(x){ return x.state === 'listed'; })[0] || null; } } catch (eLs) { _lst = null; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2878 - the shelf card marks no cell",
     "file": "bible.html",
     "find": "          + (_lsc ? '<span class=\"vm-cell-listed\" data-trade=\"listed\" title=\"' + esc(window._vaultListedSay(_lsc)) + '\">listed</span>' : '')   /* REG-2878 */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2878 - the slot reader reads a stale store text (a listing made after the first read never shows)",
     "file": "bible.html",
     "find": "    if (!_vaultTradeMemo || _vaultTradeMemo.raw !== raw) {\n",
     "replace": "    if (!_vaultTradeMemo) {\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
