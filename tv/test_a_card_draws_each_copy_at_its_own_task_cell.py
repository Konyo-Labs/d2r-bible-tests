# -*- coding: utf-8 -*-
"""REG-2876 (v3830 second eye on REG-2782, reproduced first) - THE CARD DRAWS COPY N AT COPY N'S OWN TASK CELL.

The finding: _muleLoad numbered drawn copies k = 0, 1, 2 ... by position in its filtered list and gave the k-th one the k-th
task cell _vaultPlanOn kept (only this locker's non-throw tasks, sorted by copyIx).

REPRODUCED (whole page, node): Case A - two Gulls on UNI-WEAPONS; copy 0 a throw, copy 1's task stash:c3r0. The plan held
one cell (copy 1's), yet the tile at (3,0) was key "Gull (dagger)" - copy 0 - and copy 1 ("Gull (dagger) #2") was packed
at (0,0). The move list said copy 1 sits at (3,0); the card had the other copy there; and a drag of that tile re-targets
the copy its key names (REG-2787), so it moved copy 0's task. The same numbering ran on a WAR mule, whose over-cap copies
start at copyIx 1.

Case B (a copy worn on the doll) measured NOT A DEFECT: with 3 Gulls filed on UNI-WEAPONS (tasks c0r0, c1r0, c2r0) and one
worn, the card drew "Gull (dagger)" at (0,0) and "#2" at (1,0) - each copy at its own task cell. Which copy is worn is not
recorded anywhere, so the copy left undrawn (copy 2) is the worn one, and nothing is drawn at a cell of another copy.

Now each drawn copy is keyed by its own copyIx: the copies this locker's plan names come first, in copyIx order, the rest take
the copyIx left, and a copy takes the plan cell whose copyIx is its own. Whole page in node, never a browser. RED_PROOF below.
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
var W = window, GULL = 'Gull (dagger)', SH = 'Harlequin Crest (Shako)';
function tiles(id, name){ W.openMuleCard(id); var h = (document.getElementById('vault-detail') || {}).innerHTML || '';
  var out = {}, re = /data-key="([^"]+)" data-x="(\d+)" data-y="(\d+)"/g, m;
  while ((m = re.exec(h))) if (m[1].indexOf(name) === 0) out[m[1]] = 'stash:c' + m[2] + 'r' + m[3];
  if (W.vaultCloseCard) W.vaultCloseCard(true); return out; }
function key(n, ci){ return W._muleItemKey(n, ci); }
"""
CASE_A = LIB + r"""
W._vaultAutoIntakeSet(false);
['Gull', 'Gull'].forEach(function(n){ W.vaultHandAdd(n); }); W.renderVault(); H.flush(60, 3);
W._vaultMoveCommit([{ name: GULL, copyIx: 0, task: { name: GULL, kind: 'throw', from: { holder: null }, to: { holder: null }, status: 'to-move', reason: 'law' } }]);
W._vaultMoveRetargetCell(GULL, 1, 'uni-weap', 'stash:c3r0', 'law');
W.renderVault(); H.flush(60, 3);
OUT.plan = (W._vaultPlanOn('uni-weap') || {})[GULL] || null;
OUT.tiles = tiles('uni-weap', GULL);
OUT.k1 = key(GULL, 1);
"""
CASE_WAR = LIB + r"""
W._vaultAutoIntakeSet(false);
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); W.renderVault(); H.flush(60, 3);
var war = W._vaultWarMules()[0] || {};
OUT.war = war.id || null;
OUT.plan = war.id ? ((W._vaultPlanOn(war.id) || {})[SH] || null) : null;
OUT.tiles = war.id ? tiles(war.id, SH) : null;
OUT.keys = [key(SH, 1), key(SH, 2)];
"""
CASE_B = LIB + r"""
W._vaultAutoIntakeSet(false);
['Gull', 'Gull', 'Gull'].forEach(function(n){ W.vaultHandAdd(n); });
W.vaultAssign(GULL, 'uni-weap'); W.renderVault(); H.flush(60, 3);
W.LSR.setItem('d2r_muleEquip', JSON.stringify({ 'uni-weap': { setI: { rarm: { name: GULL, at: '2026-10-28T19:00:00Z' } } } }));
W.renderVault(); H.flush(60, 3);
OUT.worn = W._mpWornFor('uni-weap', null);
OUT.plan = (W._vaultPlanOn('uni-weap') || {})[GULL] || null;
OUT.tiles = tiles('uni-weap', GULL);
OUT.keys = [key(GULL, 0), key(GULL, 1), key(GULL, 2)];
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ACardDrawsEachCopyAtItsOwnTaskCell(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.a = VPN.run(CASE_A, prelude=CLAIM, timeout=300)
        cls.w = VPN.run(CASE_WAR, prelude=CLAIM, timeout=300)
        cls.b = VPN.run(CASE_B, prelude=CLAIM, timeout=300)

    def test_case_a_a_copy_after_a_throw_is_drawn_at_its_own_cell(self):
        a = self.a
        self.assertEqual(a["__boot"]["errors"], [], a["__boot"])
        self.assertEqual(a["plan"], [{"ci": 1, "tab": "personal", "page": 0, "x": 3, "y": 0}], "PREMISE: %r" % a["plan"])
        self.assertEqual(a["tiles"].get(a["k1"]), "stash:c3r0", "copy 1 is not drawn at its task cell: %r" % a["tiles"])
        self.assertNotEqual(a["tiles"].get("Gull (dagger)"), "stash:c3r0", "copy 0 sits on copy 1's cell: %r" % a["tiles"])

    def test_a_war_mules_over_cap_copies_carry_their_own_copyix(self):
        w = self.w
        self.assertTrue(w["war"], "PREMISE: the board made no WAR mule")
        self.assertEqual([p["ci"] for p in w["plan"]], [1, 2], "PREMISE: %r" % w["plan"])
        want = dict((w["keys"][i], "stash:c%dr%d" % (p["x"], p["y"])) for i, p in enumerate(w["plan"]))
        self.assertEqual(w["tiles"], want, "a WAR mule's copies are keyed by position, not by copyIx: %r vs %r" % (w["tiles"], want))

    def test_case_b_a_worn_copy_leaves_every_drawn_copy_at_its_own_cell(self):
        b = self.b
        self.assertEqual(b["worn"], {"Gull (dagger)": 1}, "PREMISE: no copy worn: %r" % b["worn"])
        self.assertEqual([p["ci"] for p in b["plan"]], [0, 1, 2], "PREMISE: %r" % b["plan"])
        cells = dict(("stash:c%dr%d" % (p["x"], p["y"]), p["ci"]) for p in b["plan"])
        self.assertEqual(len(b["tiles"]), 2, b["tiles"])
        for k, cell in b["tiles"].items():
            ci = b["keys"].index(k)
            self.assertEqual(cells.get(cell), ci, "a drawn copy sits on another copy's cell: %s at %s" % (k, cell))


RED_PROOF = [
    {"why": "REG-2876 - a drawn copy is keyed by its position again (copy 0's key on copy 1's cell)",
     "file": "bible.html",
     "find": "        sized.push({n:n, key:_muleItemKey(n, _cis[_ci]), ci:_cis[_ci],",
     "replace": "        sized.push({n:n, key:_muleItemKey(n, _ci), ci:_cis[_ci],",
     "matches": 1, "needs": "node"},
    {"why": "REG-2876 - the plan's copies are not drawn first (a copy with no cell here takes the first key)",
     "file": "bible.html",
     "find": "      pl.forEach(function(q){ if (out.indexOf(q.ci) < 0 && out.length < m) out.push(q.ci); });\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2876 - a WAR mule's over-cap copies are keyed by position",
     "file": "bible.html",
     "find": "          sized.push({n:n, key:_muleItemKey(n, _wcis[_wi]), ci:_wcis[_wi],",
     "replace": "          sized.push({n:n, key:_muleItemKey(n, _wi), ci:_wi,",
     "matches": 1, "needs": "node"},
    {"why": "REG-2876 - a drawn copy's copyIx is its position, so the plan cell goes to another copy's key",
     "file": "bible.html",
     "find": "        sized.push({n:n, key:_muleItemKey(n, _cis[_ci]), ci:_cis[_ci],",
     "replace": "        sized.push({n:n, key:_muleItemKey(n, _cis[_ci]), ci:_ci,",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
