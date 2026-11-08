# -*- coding: utf-8 -*-
"""#153 — the character build's STASH opens the same stash view as the mule window.

Inventory, Personal and Shared. One tab function, _stabHtml, lives in the vault span and is
what both windows call. The grids are this build's: Inventory is the active set (10x4, stored
cells kept), Personal is b.stash and Shared is b.shared (each 10x10, packed for the view, not
written back). Vault 2.0 and the mule's five tabs stay the mule's.

The builder harness does not load the vault span, so the tab function is injected from its
markers. A copy pasted into the builder would make this law green on a path the page never
runs; the modal must contain the string window._stabHtml actually returned.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

from cb_node_harness import NODE, _run, _src  # noqa: E402


MULE_PERSONAL = (
    '<button type="button" class="vd-tab vt-on" role="tab" aria-selected="true" '
    'data-tab="personal" data-fk="stab-personal" '
    "onclick=\"window._mpSet('stab','personal')\" "
    'title="Personal tab of Mule 1 \u2014 empty (the packer fills this one). '
    'Drop an item on the tab to move it here">Personal</button>'
)


@unittest.skipIf(NODE is None, "node is not on this machine")
class TheBuildStashIsTheMuleStashView(unittest.TestCase):

    def test_one_function_paints_the_mule_tab_and_the_build_tabs(self):
        src = _src()
        self.assertEqual(src.count("function _stabHtml("), 1, "the tab row is not one function")
        out = _run(r"""
          OUT.mulePersonal = window._stabHtml([{
            id: 'personal', on: true, n: 0, label: 'Personal', badge: false,
            onclick: "window._mpSet('stab','personal')",
            title: 'Personal tab of Mule 1 \u2014 empty (the packer fills this one). Drop an item on the tab to move it here'
          }]);
          OUT.sharedBadge = window._stabHtml([{
            id: 'shared', on: false, n: 2, label: 'Shared', badge: true,
            onclick: "window._mpSet('stab','shared')",
            title: 'Shared tab'
          }]);
          OUT.personalBare = window._stabHtml([{
            id: 'personal', on: true, n: 4, label: 'Personal', badge: false,
            onclick: "window._mpSet('stab','personal')",
            title: 'Personal tab'
          }]);
          READS.length = 0;
          window.openCharBuilder();
          var d = window._cbDb();
          var pick = function(n){ var h = null; d.it.forEach(function(x){ if (x[1] === n) h = x; }); return h ? h[0] : null; };
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose(pick('Annihilus'));
          window._cbOpenStash();
          var personalBtn = window._stabHtml([{
            id: 'personal', on: true, n: 0, label: 'Personal', badge: false,
            onclick: "window._cbStashArea('personal')",
            title: 'Personal of this build. Items this build keeps.'
          }]);
          OUT.personalJoined = personalBtn.length > 20 && MODAL._html.indexOf(personalBtn) >= 0;
          OUT.three = ['inv', 'personal', 'shared'].every(function(id){
            return MODAL._html.indexOf('data-tab="' + id + '"') >= 0 && MODAL._html.indexOf('data-fk="stab-' + id + '"') >= 0;
          });
          OUT.personalOn = MODAL._html.indexOf('class="vd-tab vt-on" role="tab" aria-selected="true" data-tab="personal"') >= 0;
          function cells(){ return (MODAL._html.match(/class="cb-bag-cell"/g) || []).length; }
          OUT.personalCells = cells();
          OUT.noWornClass = MODAL._html.indexOf('class="cb-it"') < 0;
          window._cbStashArea('inv');
          OUT.invCells = cells();
          OUT.anni = MODAL._html.indexOf('class="cb-bag-it" style="grid-column:1 / span 1;grid-row:1 / span 1"') >= 0
            && MODAL._html.indexOf('>Annihilus</button>') >= 0;
          OUT.invNoWorn = MODAL._html.indexOf('class="cb-it"') < 0;
          window._cbStashArea('personal');
          window._cbStashTab('create'); window._cbStashCat(1); window._cbStashAdd(pick('Harlequin Crest'));
          window._cbStashTab('stash');
          OUT.shako = MODAL._html.indexOf('class="cb-bag-it"') >= 0 && MODAL._html.indexOf('Harlequin Crest') >= 0;
          var cur = function(){ var all = window._cbAll(); return all[window._cbState().bid]; };
          OUT.stash = (cur().stash || []).map(function(e){ return e.name; });
          OUT.shared = (cur().shared || []).map(function(e){ return e.name; });
          window._cbStashArea('shared');
          window._cbStashTab('create'); window._cbStashAdd(pick('Annihilus'));
          window._cbStashTab('stash');
          OUT.sharedGrid = MODAL._html.indexOf('Harlequin Crest') < 0 && MODAL._html.indexOf('>Annihilus <small>remove</small>') >= 0;
          OUT.sharedCells = cells();
          OUT.stashAfter = (cur().stash || []).map(function(e){ return e.name; });
          OUT.sharedAfter = (cur().shared || []).map(function(e){ return e.name; });
          window._cbStashDropAt('personal', 0);
          window._cbStashArea('personal');
          OUT.dropped = MODAL._html.indexOf('Harlequin Crest') < 0;
          OUT.stashDropped = (cur().stash || []).map(function(e){ return e.name; });
          window._cbCommit(function(b){ delete b.shared; });
          window._cbStashArea('shared');
          OUT.oldSharedCells = cells();
          OUT.card = ELS['cb-win']._html.indexOf('Inventory, Personal and Shared. Grids that belong to this build, never the vault.') >= 0;
          OUT.reads = READS.filter(function(k, i){ return READS.indexOf(k) === i; });
          OUT.calls = CALLS;
        """)
        self.assertEqual(out["mulePersonal"], MULE_PERSONAL, "the empty Personal tab is not the mule's button")
        self.assertIn(">Shared <b>2</b></button>", out["sharedBadge"])
        self.assertNotIn("<b>", out["personalBare"], "Personal shows a count, and the mule never badges it")
        self.assertTrue(out["personalJoined"], "the build's Personal tab is not the string _stabHtml returned")
        self.assertTrue(out["three"], "Inventory, Personal and Shared are not all on the build stash")
        self.assertTrue(out["personalOn"], "Personal is not the tab that opens")
        self.assertEqual(out["personalCells"], 100)
        self.assertEqual(out["invCells"], 40)
        self.assertEqual(out["sharedCells"], 100)
        self.assertTrue(out["anni"], "the inventory charm is not on its cell in the Inventory tab: the grid did not keep the stored cell")
        self.assertTrue(out["noWornClass"] and out["invNoWorn"], "a stash cell used the worn-item class")
        self.assertTrue(out["shako"], "Create did not draw Harlequin Crest on the Personal grid")
        self.assertEqual(out["stash"], ["Harlequin Crest"])
        self.assertEqual(out["shared"], [])
        self.assertTrue(out["sharedGrid"], "Shared drew the Personal item, or missed its own")
        self.assertEqual(out["stashAfter"], ["Harlequin Crest"])
        self.assertEqual(out["sharedAfter"], ["Annihilus"])
        self.assertTrue(out["dropped"], "removing the Personal item left it on the grid")
        self.assertEqual(out["stashDropped"], [])
        self.assertEqual(out["oldSharedCells"], 100, "a saved build with no shared list did not open an empty Shared grid")
        # v3885 (#134, his DESIGN C rule 1, 11-08: "Remove Stash from the character build screen, button and panel") - the build
        # screen draws NO stash card now; the stash view itself (opened above, three grids) still serves the mule window
        self.assertFalse(out["card"], "the Stash card is back on the character build screen (his Design C rule 1)")
        self.assertEqual(sorted(out["reads"]), ["d2r_cbMain", "d2r_cbSel", "d2r_charBuilds"],
                         "the builder read a store that is not its own: %s" % out["reads"])
        self.assertEqual(out["calls"], [], "the builder called the vault or a mule: %s" % out["calls"])


RED_PROOF = [
    {
        "why": "#153 the one tab function returns nothing, so the build stash and the mule both lose Inventory, Personal and Shared",
        "file": "bible.html",
        "find": "  function _stabHtml(rows){\n    return (rows || []).map(function(r){\n",
        "replace": "  function _stabHtml(rows){\n    return '';\n    return (rows || []).map(function(r){\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
