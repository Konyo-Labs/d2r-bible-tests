# -*- coding: utf-8 -*-
"""REG-2887 (#231 second eye on v3833: "the shared stash draws the k-th kept copy at the k-th cell of the filtered task
list ... The copy index is stored on the task and is not the join") - THE SHARED STASH DRAWS EACH COPY AT ITS OWN TASK CELL.

REG-2801's _sharedLayout copied REG-2782's k-th-cell rule, the one REG-2876 removed from the mule card. The shared stash's
plan (_vaultPlanOn('shared')) is FILTERED: a throw, a task with no cell, a cell that will not parse and another holder's
task are dropped. It is then sorted by copyIx. The draw walked k = 0, 1, 2, took plan[k] and keyed the tile as copy k.
MEASURED (whole page in node): Death's Fathom x2, copy 0 a throw, copy 1's task on page 2 (col 4, row 3). The layout drew
key "Death's Fathom" (copy 0) at copy 1's cell. A listing of copy 1 then put its mark on whichever tile copy 1's key landed
on, and a drag of the tile at copy 1's cell re-targeted copy 0.

Now the shared stash goes through the mule card's own join (_vaultPlanCis / _vaultPlanCell, one helper for both). The copies
the plan names come first in copyIx order, each keyed by its own copyIx, and each takes the task cell of that copyIx. Whole
page in node, never a browser. RED_PROOF below.
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
LIB = r"""
var W = window, DF = "Death's Fathom";
function lay(){ var L = W._sharedLayout([DF]), out = {};
  (L.pages || []).forEach(function(pg, pi){ pg.forEach(function(o){ if (o.n === DF) out[o.key] = 'p' + pi + ':c' + o.x + 'r' + o.y; }); });
  return out; }
function listedTiles(page){ W._sharedSetPage(page); W.openMuleCard('shared'); H.flush(60, 3);
  var h = (document.getElementById('vault-detail') || {}).innerHTML || '', out = [], re = /<div class="vd-item[^"]*vd-listed[^"]*" style="left:(\d+)px;top:(\d+)px/g, m;
  while ((m = re.exec(h))) out.push([+m[1], +m[2]]);
  if (W.vaultCloseCard) W.vaultCloseCard(true); return out; }
W._vaultAutoIntakeSet(false);
W.vaultHandAdd(DF); W.vaultHandAdd(DF); W.renderVault(); H.flush(60, 3);
"""
THROW = LIB + r"""
W._vaultMoveCommit([{ name: DF, copyIx: 0, task: { name: DF, kind: 'throw', from: { holder: null }, to: { holder: null }, status: 'to-move', reason: 'law' } }]);
W._vaultMoveRetargetCell(DF, 1, 'shared', 'shared:c3r12', 'law');
W._vaultTradeEvent({ kind: 'listed', name: DF, copyIx: 1 });
W.renderVault(); H.flush(60, 3);
OUT.plan = (W._vaultPlanOn('shared') || {})[DF] || null;
OUT.lay = lay();
OUT.listed = listedTiles(1);
OUT.keys = [W._muleItemKey(DF, 0), W._muleItemKey(DF, 1)];
"""
NOCELL = LIB + r"""
W._vaultMoveCommit([{ name: DF, copyIx: 0, task: { name: DF, from: { holder: null }, to: { holder: 'SHARED STASH', location: 'shared', cell: null, id: 'shared' }, status: 'to-move', reason: 'law', manual: true } }]);
W._vaultMoveRetargetCell(DF, 1, 'shared', 'shared:c6r0', 'law');
W.renderVault(); H.flush(60, 3);
OUT.plan = (W._vaultPlanOn('shared') || {})[DF] || null;
OUT.lay = lay();
OUT.keys = [W._muleItemKey(DF, 0), W._muleItemKey(DF, 1)];
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheSharedStashDrawsEachCopyAtItsOwnTaskCell(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.t = VPN.run(THROW, prelude=CLAIM, timeout=300)
        cls.n = VPN.run(NOCELL, prelude=CLAIM, timeout=300)

    def test_copy_one_after_a_thrown_copy_zero_is_drawn_at_its_own_page_cell(self):
        t = self.t
        self.assertEqual(t["__boot"]["errors"], [], t["__boot"])
        self.assertEqual(t["plan"], [{"ci": 1, "tab": "sharedpage", "page": 1, "x": 3, "y": 2}], "PREMISE: %r" % t["plan"])
        k0, k1 = t["keys"]
        self.assertEqual(t["lay"].get(k1), "p1:c3r2", "copy 1 is not drawn at its task cell: %r" % t["lay"])
        self.assertNotEqual(t["lay"].get(k0), "p1:c3r2", "copy 0 is painted at copy 1's cell: %r" % t["lay"])

    def test_the_listed_mark_of_copy_one_sits_on_copy_ones_cell(self):
        tiles = self.t["listed"]
        self.assertEqual(len(tiles), 1, "PREMISE: not exactly one listed tile on page 2: %r" % tiles)
        left, top = tiles[0]
        self.assertTrue(left > 3 and (left - 3) * 2 == (top - 3) * 3,
                        "the listed mark is not at col 4, row 3 (copy 1's cell): left %d, top %d" % (left, top))

    def test_copy_one_after_a_cell_less_copy_zero_is_drawn_at_its_own_cell(self):
        n = self.n
        self.assertEqual(n["__boot"]["errors"], [], n["__boot"])
        self.assertEqual([(p["ci"], p["page"], p["x"], p["y"]) for p in n["plan"]], [(1, 0, 6, 0)], "PREMISE: %r" % n["plan"])
        k0, k1 = n["keys"]
        self.assertEqual(n["lay"].get(k1), "p0:c6r0", "copy 1 is not drawn at its task cell: %r" % n["lay"])
        self.assertNotEqual(n["lay"].get(k0), "p0:c6r0", "copy 0 is painted at copy 1's cell: %r" % n["lay"])

    def test_one_join_serves_the_mule_card_and_the_shared_stash(self):
        with open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        code = re.sub(r"/\*[\s\S]*?\*/", "", src)
        self.assertEqual(code.count("function _vaultPlanCis("), 1)
        self.assertNotRegex(code, r"_muleItemKey\(n, k\), c = pl\[k\]", "the shared stash walks k against the filtered plan again")
        self.assertEqual(len(re.findall(r"_vaultPlanCis\(", code)), 3, "a locker joins copies to cells some other way")


RED_PROOF = [
    {"why": "REG-2887 - the shared stash keys and places the k-th copy by position again",
     "file": "bible.html",
     "find": "        var key = _muleItemKey(n, cis[k]), c = _vaultPlanCell(pl, cis[k]);",
     "replace": "        var key = _muleItemKey(n, k), c = pl[k];",
     "matches": 1, "needs": "node"},
    {"why": "REG-2887 - the join hands out copyIx by position, not the plan's own copies first",
     "file": "bible.html",
     "find": "    (pl || []).forEach(function(q){ if (out.indexOf(q.ci) < 0 && out.length < m) out.push(q.ci); });\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
