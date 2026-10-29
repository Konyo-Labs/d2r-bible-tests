# -*- coding: utf-8 -*-
"""Vault L1 - EVERY hand add is a MOVE TASKS row: 'MANUAL -> <mule> (x,y)'. A set piece he types is kept.

Elad, live v3774 (2026-10-20): he hand-added a set item and saw no move task. A ruled-low set (Sigon's,
Cathan's, Isenhart's) typed through + Add an item fell to a THROW OUT row (NOWHERE), so his add had no move.
His typing is the ruling: it is kept and routed to the sets mule. Driven on the SHIPPED page through the real
door (window.vaultHandAdd), AUTO INTAKE off: a batch of 20 hand adds (8 set pieces, 4 of them ruled-low) must
paint exactly 20 open rows in the right-side MOVE TASKS list, each a MANUAL move to a real mule at a real (x,y),
none a THROW OUT. NO CHROME AT ALL = a declared skip, never a pass. RED_PROOF below. [[regression-guard]]
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_vault_l1_a_hand_add_routes_by_type as T  # noqa: E402  (reuse its board, door and reader)
H = T.H

SETS = ["Sigon's Guard", "Sigon's Visor", "Cathan's Mesh", "Isenhart's Case",
        "Arcanna's Sign", "Tal Rasha's Guardianship", "Trang-Oul's Claws", "Aldur's Advance"]
BATCH = SETS + ["Immortal King's Stone Crusher", "Natalya's Mark", "Griswold's Heart", "M'avina's Embrace",
                "Harlequin Crest", "Insight", "Gheed's Fortune", "Rainbow Facet", "Nokozan Relic",
                "Arachnid Mesh", "Enigma", "Stone of Jordan"]
# REG-2789 - a shared stash row names its page, never the old "tab N" - since REG-3005 in the one spelling
# ("SHARED STASH · Page 2 · col 1 · row 3"); a mule row still reads "MULE1 (x,y)"
# REG-3062: a mule row in the one spelling too ("SETS-REST · Mule 2 · Personal stash · col 3 · row 1")
LINE = re.compile(r"MANUAL → ([A-Z][A-Z0-9\- ]+?) · (?:Page [1-5] · col (\d+) · row (\d+)|(?:Mule \d+ · )?[A-Z][a-z]+(?: stash)? · col (\d+) · row (\d+))")

ROWS = (T.READ + "var host = document.getElementById('vault-move-list');"
        "OUT.rows = host ? Array.prototype.map.call(host.querySelectorAll('.vtk-list:not([data-sec=\"done\"]) .vmv-row'), function(r){"
        "  return { name: r.getAttribute('data-name'), kind: r.getAttribute('data-kind'),"
        "           manual: !!r.querySelector('.vmv-manual-badge'), text: r.textContent.replace(/\\s+/g, ' ') }; }) : null;"
        "OUT.dock = window._vaultDockNames();")


def tearDownModule():
    T.tearDownModule()


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class EveryHandAddIsAMoveTask(unittest.TestCase):

    def _check(self, typed, o, add):
        rows = o["rows"]
        self.assertIsNotNone(rows, "MOVE TASKS (#vault-move-list) is not on the page")
        for n in typed:
            self.assertTrue(add[n]["ok"], "the hand door refused %s: %r" % (n, add[n]))
        names = [add[n]["name"] for n in typed]
        for nm in names:
            mine = [r for r in rows if r["name"] == nm]
            self.assertEqual(len(mine), 1, "%s has %d open rows, not one: %r" % (nm, len(mine), mine))
            r = mine[0]
            self.assertNotEqual(r["kind"], "throw", "his hand add became a THROW OUT row: %r" % r)
            self.assertTrue(r["manual"], "%s row has no MANUAL badge: %r" % (nm, r))
            m = LINE.search(r["text"])
            self.assertIsNotNone(m, "%s does not read 'MANUAL → <mule> (x,y)': %r" % (nm, r["text"]))
            self.assertNotIn("NOWHERE", r["text"])
            self.assertNotIn(nm, o["dock"] or [], "%s waits in the Unsorted Dock" % nm)
        self.assertEqual(len([r for r in rows if r["name"] in names]), len(typed))

    def test_one_hand_typed_ruled_low_set_piece_is_a_manual_move(self):
        T.fresh()
        a = T.add_all(["Sigon's Guard"])["add"]
        o = T.board().run(ROWS)
        self._check(["Sigon's Guard"], o, a)
        r = [x for x in o["rows"] if x["name"] == a["Sigon's Guard"]["name"]][0]
        self.assertIn("SETS-", r["text"], "a typed set piece did not route to a sets mule: %r" % r)

    def test_a_batch_of_twenty_hand_adds_is_twenty_rows(self):
        T.fresh()
        a = T.add_all(BATCH)["add"]
        o = T.board().run(ROWS)
        self.assertEqual(len(BATCH), 20)
        self._check(BATCH, o, a)
        for s in SETS:
            r = [x for x in o["rows"] if x["name"] == a[s]["name"]][0]
            self.assertRegex(r["text"], r"MANUAL → SETS-", "set piece %s not routed to a sets mule: %r" % (s, r))

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import wilson_lower
        import self_arming as SA
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        print("vault L1 every hand add: %d distinct attacks, wilson %.4f vs bar %.3f" % (n, w, SA.LOCKS["vault.apply"]["bar"]))
        self.assertGreaterEqual(w, SA.LOCKS["vault.apply"]["bar"])


RED_PROOF = [
    {'why': 'A typed set piece is not kept at all - every one falls to throw-out.', 'file': 'bible.html', 'find': "        return { loc: 'filed', mule: 'sets-rest' }; /* L1 he typed a set piece: kept, not thrown out */", 'replace': "        return { loc: 'loose', mule: null }; /* L1 he typed a set piece: kept, not thrown out */", 'matches': 1},
    {'why': 'The hand receipt is not read, so no hand add is known as his.', 'file': 'bible.html', 'find': "      if (p && p.source === 'hand' && /Add an item|Vault planner|the Vault/.test(String(p.where || '') + ' ' + String(p.by || ''))) return true;", 'replace': '      if (false) return true;', 'matches': 1},
    {'why': "A hand add's row loses its MANUAL badge.", 'file': 'bible.html', 'find': '+ (manual ? \'<b class="vmv-manual-badge">MANUAL</b>\' : esc(_vtkPlace(t.from, false)))', 'replace': "+ (manual ? '<b>HAND</b>' : esc(_vtkPlace(t.from, false)))", 'matches': 1},
    {'why': "A hand add's row says NOWHERE instead of its mule and cell.", 'file': 'bible.html', 'find': '\' → \' + (thr ? \'<b class="vmv-nowhere">NOWHERE</b>\' : \'<span class="vtk-to">\' + esc(_vtkPlace(t.to, false)) + \'</span>\')', 'replace': '\' → \' + ((thr || manual) ? \'<b class="vmv-nowhere">NOWHERE</b>\' : \'<span class="vtk-to">\' + esc(_vtkPlace(t.to, false)) + \'</span>\')', 'matches': 1},
    {'why': "The row drops its target cell: 'MANUAL → SETS-REST' with no cell.", 'file': 'bible.html', 'find': "      if (_ca) return h + ' · ' + _muleSpotSay(_ca.loc, _ca.x, _ca.y, _ca.page > 0 ? _ca.page : null);", 'replace': '      if (_ca) return h;', 'matches': 1},
    {'why': 'The row never knows it is a hand add, so it prints a FROM place instead of MANUAL.', 'file': 'bible.html', 'find': '      var manual = !!(t.manual && !(t.from && t.from.cell != null));', 'replace': '      var manual = false;', 'matches': 1},
    {'why': "A hand add's row is painted in the closed Done section, not the open list.", 'file': 'bible.html', 'find': "    function _vtkDone(t){ return t && (t.status === 'moved-manual' || t.status === 'verified' || t.status === 'closed'); }", 'replace': "    function _vtkDone(t){ return t && (t.manual || t.status === 'moved-manual' || t.status === 'verified' || t.status === 'closed'); }", 'matches': 1},
    {'why': 'A junk-routed item returns to throw-out before any hand check (every typed ruled-low set piece is a THROW OUT row again).', 'file': 'bible.html', 'find': "      if (sg.id === '__keep') return { loc: 'keep', mule: null };\n", 'replace': "      if (sg.id === '__throwout') return { loc: 'loose', mule: null };\n      if (sg.id === '__keep') return { loc: 'keep', mule: null };\n", 'matches': 1},
    {'why': 'Nothing is ever known as hand-typed.', 'file': 'bible.html', 'find': '  function _vaultHandTyped(n){\n    try {', 'replace': '  function _vaultHandTyped(n){ return false;\n    try {', 'matches': 1},
    {'why': 'A typed set piece is filed to the war stash, not a sets mule.', 'file': 'bible.html', 'find': "        return { loc: 'filed', mule: 'sets-rest' }; /* L1 he typed a set piece: kept, not thrown out */", 'replace': "        return { loc: 'shared', mule: null }; /* L1 he typed a set piece: kept, not thrown out */", 'matches': 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
