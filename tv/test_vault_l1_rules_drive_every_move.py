# -*- coding: utf-8 -*-
"""Vault L1 - moves come from the placement rules; no Fix / Auto-assign press is ever needed.

Elad's standing rule (2026-10-20), after the v3776 live click-through on his real data:
  - a hand-added copy of an item he already owns (Demon Limb filed on UNI-WEAPONS before it became war gear) routes by
    the CURRENT rules to its own cell and always gets its own MANUAL row - never 'in place' with no row;
  - an item filed where the rules no longer put it (war gear on a UNI-* mule: a VAULT INTEGRITY mismatch) gets a move
    row FROM its mule TO the rules' home, automatically; a correctly filed item gets none; the filing (assign) is not
    rewritten - the row is the instruction;
  - copies of one item land beside each other when space allows (the free cell nearest the sibling copy).
Driven on the SHIPPED page (window.vaultHandAdd, window._vaultMovePaint), AUTO INTAKE off. RED_PROOF below.
NO CHROME AT ALL = a declared skip, never a pass. [[regression-guard]]
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_vault_l1_a_hand_add_routes_by_type as T  # noqa: E402  (its board, door and reader)
H = T.H

ROWS = r"""
function rows(){ window._vaultMovePaint(); var h = document.getElementById('vault-move-list'); return h ? Array.prototype.map.call(h.querySelectorAll('.vtk-list:not([data-sec="done"]) .vmv-row'), function(r){ return { n: r.getAttribute('data-name'), t: r.textContent.replace(/\s+/g, ' ') }; }) : null; }
"""


def tearDownModule():
    T.tearDownModule()


def _filed(mule):
    return {"mule": mule, "holder": mule, "source": "hand", "where": "the vault manager", "by": "hand",
            "at": "2026-10-07T08:00:00.000Z", "sessions": [], "looks": [], "ver": "law"}


def seed_misfiled():
    T.board().seed({"d2r_owned": ["Demon Limb", "Enigma", "Nokozan Relic"],
                    "d2r_muleAssign": {"Demon Limb": "uni-weap", "Enigma": "runewords", "Nokozan Relic": "uni-small"},
                    "d2r_vaultProv": {"Demon Limb": _filed("uni-weap"), "Enigma": _filed("runewords"), "Nokozan Relic": _filed("uni-small")},
                    "d2r_vaultRecords": None, "d2r_copies": {}, "d2r_multiKeep": {}})
    T.board().run("window._vaultAutoIntakeSet(false); try { window.switchTab('vault'); } catch (e) {} OUT.ok = 1;")


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class RulesDriveEveryMove(unittest.TestCase):

    def test_a_new_copy_of_an_owned_misfiled_item_routes_by_the_rules_with_its_own_row(self):
        seed_misfiled()
        o = T.board().run(T.READ + ROWS + "var a = window.vaultHandAdd('Demon Limb'); OUT.a = { ok: a.ok, mode: a.mode, shown: !!(a.move && a.move.shown), why: (a.move && a.move.why) || null, to: (a.move && a.move.task && a.move.task.to) || null };"
                          "OUT.rows = rows().filter(function(r){ return r.n === 'Demon Limb'; });")
        self.assertEqual(o["a"]["mode"], "copy", o["a"])
        self.assertNotEqual(o["a"]["why"], "in place", "the new copy was 'in place' with no row: %r" % o["a"])
        self.assertTrue(o["a"]["shown"], o["a"])
        # Elad 2026-10-20: the war stash keeps ONE copy of a big item (the owned, first-witnessed one); this
        # extra copy goes to its normal mule - by the rules, with its own row, never 'in place'
        self.assertEqual((o["a"]["to"] or {}).get("holder"), "UNI-WEAPONS", "the extra big copy did not go to its normal mule: %r" % o["a"])
        self.assertTrue((o["a"]["to"] or {}).get("cell"), "the copy got no cell: %r" % o["a"])
        manual = [r for r in o["rows"] if "MANUAL" in r["t"]]
        self.assertEqual(len(manual), 1, "the hand copy has no MANUAL row of its own: %r" % o["rows"])
        self.assertRegex(manual[0]["t"], r"MANUAL → UNI-WEAPONS \(\d+,\d+\)")

    def test_a_misfiled_item_gets_a_move_row_from_its_mule_with_no_press(self):
        seed_misfiled()
        o = T.board().run(T.READ + ROWS + "OUT.rows = rows(); OUT.a = JSON.parse(window.LSR.getItem('d2r_muleAssign') || '{}');")
        by = {}
        for r in o["rows"] or []:
            by.setdefault(r["n"], []).append(r["t"])
        self.assertIn("Enigma", by, "war gear filed on RUNEWORDS got no move row: %r" % o["rows"])
        self.assertRegex(by["Enigma"][0], r"RUNEWORDS → SHARED STASH · Page \d · col \d+ · row \d+")   # REG-2802 "page"; REG-3005 the one spelling
        self.assertIn("Demon Limb", by, "war gear filed on UNI-WEAPONS got no move row: %r" % o["rows"])
        self.assertRegex(by["Demon Limb"][0], r"UNI-WEAPONS → SHARED STASH")
        self.assertNotIn("Nokozan Relic", by, "a correctly filed item got a move row")
        self.assertEqual(o["a"].get("Enigma"), "runewords", "the filing was rewritten - the row is the instruction, not a silent re-file")

    def test_copies_cluster_on_the_nearest_free_cell(self):
        o = T.board().run("var pg = window._vaultPackGrid;"
                          "var occ = [{ x: 2, y: 0, w: 2, h: 2 }];"
                          "var r = pg([{ n: 'A', key: 'A0', w: 2, h: 3, cluster: true }, { n: 'A', key: 'A1', w: 2, h: 3, cluster: true }], 10, 10, occ);"
                          "OUT.c = r.placed.map(function(p){ return [p.key, p.x, p.y]; });"
                          "var s = pg([{ n: 'B', key: 'B1', w: 2, h: 3, near: { x: 6, y: 4 } }], 10, 10, []);"
                          "OUT.s = s.placed.map(function(p){ return [p.key, p.x, p.y]; });")
        self.assertEqual(o["c"], [["A0", 0, 0], ["A1", 0, 3]], "the 2nd copy did not land beside the 1st: %r" % o["c"])
        self.assertEqual(o["s"], [["B1", 6, 4]], "a copy did not take the free cell at its saved sibling: %r" % o["s"])

    def test_two_hand_copies_land_side_by_side_on_the_mule(self):
        T.fresh()
        T.add_all(["Aldur's Deception", "Aldur's Deception"])
        o = T.board().run(T.READ + "OUT.m = recs().filter(function(r){ return /^Aldur's Deception/.test(r.name) && r.move; }).map(function(r){ return r.move.to; });")
        xy = []
        for t in o["m"]:
            import re
            m = re.match(r"^\w+:c(\d+)r(\d+)$", str(t.get("cell")))
            self.assertTrue(m, o["m"])
            xy.append((int(m.group(1)), int(m.group(2))))
        self.assertEqual(len(xy), 2, o["m"])
        (x0, y0), (x1, y1) = xy
        self.assertTrue((abs(x0 - x1) == 2 and y0 == y1) or (abs(y0 - y1) == 3 and x0 == x1), "the two copies are not adjacent: %r" % xy)

    def test_two_copies_close_per_copy_never_swapped(self):
        """Elad 2026-10-20: two copies at two cells are two rows; a sighting at copy A's target closes only A; B stays
        open until B is seen at ITS target"""
        T.fresh()
        T.add_all(["Aldur's Deception", "Aldur's Deception"])
        js = T.READ + r"""
var st = JSON.parse(LSR.getItem('d2r_vaultRecords')); var mine = st.records.filter(function(r){ return /^Aldur's Deception/.test(r.name) && r.move; });
mine.forEach(function(r, i){ r.move.from = { holder: 'MAIN', location: 'stash', cell: 'c' + (i * 5) + 'r0' }; r.move.manual = false; });
LSR.setItem('d2r_vaultRecords', JSON.stringify(st));
function st2(){ return (JSON.parse(LSR.getItem('d2r_vaultRecords')).records || []).filter(function(r){ return /^Aldur's Deception/.test(r.name) && r.move; })
  .map(function(r){ return [r.copyIx || 0, r.move.status]; }).sort(); }
var A = mine[0], B = mine[1]; OUT.nm = A.name; OUT.cells = [A.move.to.cell, B.move.to.cell];
OUT.s0 = st2();
/* REG-2843 - his done rule: a full look of the target is one session; two sessions read after the task opened close it */
var T0 = Date.now();
function look(n, at, items){ var ms = T0 + n * 60000; return { session: 's_' + ms + '_' + n, at: new Date(ms).toISOString(), holder: at.holder, location: at.location, items: items, ground: [] }; }
window._vaultGoneObserve(look(1, A.move.to, [{ name: A.name, cell: A.move.to.cell }]));
OUT.h1 = st2();
window._vaultGoneObserve(look(2, A.move.to, [{ name: A.name, cell: A.move.to.cell }]));
OUT.s1 = st2(); OUT.a = A.copyIx || 0;
window._vaultGoneObserve(look(3, B.move.to, [{ name: A.name, cell: A.move.to.cell }, { name: B.name, cell: B.move.to.cell }]));
window._vaultGoneObserve(look(4, B.move.to, [{ name: A.name, cell: A.move.to.cell }, { name: B.name, cell: B.move.to.cell }]));
OUT.s2 = st2();
"""
        o = T.board().run(js)
        self.assertEqual(len(o["s0"]), 2, "PREMISE: two copies, two rows: %r" % o["s0"])
        self.assertNotEqual(o["cells"][0], o["cells"][1], o["cells"])
        self.assertEqual([x[1] for x in o["s0"]], ["to-move", "to-move"])
        self.assertEqual([x[1] for x in o["h1"]], ["to-move", "to-move"], "one full look closed a task (REG-2843 wants two sessions): %r" % o["h1"])
        st1 = dict((c, s) for c, s in o["s1"])
        self.assertEqual(st1[o["a"]], "verified", "copy A seen at its target did not close: %r" % o["s1"])
        self.assertEqual([s for c, s in o["s1"] if c != o["a"]], ["to-move"], "one sighting closed BOTH copies' rows: %r" % o["s1"])
        self.assertEqual([x[1] for x in o["s2"]], ["verified", "verified"], "copy B seen at its target did not close: %r" % o["s2"])

    def test_a_hand_row_with_no_room_still_shows(self):
        o = T.board().run("OUT.v = window._vaultMoveShown({ name: 'Demon Limb', manual: true, status: 'to-move', evidence: [],"
                          " from: { holder: null, location: null, cell: null }, to: { holder: 'SHARED STASH', location: 'shared', cell: null } });")
        self.assertTrue(o["v"], "a hand add with no room has no row - it would read 'in place'")

    def test_the_panel_wraps_the_full_target_and_the_dock_line_is_plain(self):
        T.fresh()
        T.add_all(["Aldur's Deception"])
        o = T.board().run("try { window.switchTab('vault'); } catch (e) {} window._vaultMovePaint();"
                          "var s = document.querySelector('#vault-move-list .vtk-say'); var cs = s && getComputedStyle(s);"
                          "OUT.ws = cs && cs.whiteSpace; OUT.to = cs && cs.textOverflow;"
                          "var d = document.querySelector('.vault-dock'); if (d) { d.setAttribute('data-owned', '1'); d.setAttribute('data-misfiled', '1'); d.innerHTML = ''; }"
                          "OUT.dock = d ? getComputedStyle(d, '::after').content : null;")
        self.assertEqual(o["ws"], "normal", "the task line no longer wraps: %r" % o)
        self.assertNotEqual(o["to"], "ellipsis", "the task target is ellipsized: %r" % o)
        self.assertIsNotNone(o["dock"])
        self.assertNotRegex(o["dock"], r"Auto-assign|INTEGRITY", "the dock line still sends him to a button: %r" % o["dock"])

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import wilson_lower
        import self_arming as SA
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        print("vault L1 rules drive every move: %d distinct attacks, wilson %.4f vs bar %.3f" % (n, w, SA.LOCKS["vault.apply"]["bar"]))
        self.assertGreaterEqual(w, SA.LOCKS["vault.apply"]["bar"])


RED_PROOF = [
    {"why": "A stale filing wins again: war gear filed on a UNI-* mule plans its move to that mule.",
     "file": "bible.html", "find": "    if (_mis) seam = _mis.seam; /* L1 the rules' home, not a stale filing */\n",
     "replace": "", "matches": 1},
    {"why": "A misfiled item with no sighting gets no move row (it waits for a Fix / Auto-assign press).",
     "file": "bible.html", "find": "      if (!stored && !hasSight && !_vaultMisfiled(r.name)) return; /* L1 a misfiled item gets its move row */",
     "replace": "      if (!stored && !hasSight) return; /* L1 a misfiled item gets its move row */", "matches": 1},
    {"why": "The rules' war-stash home is ignored for a misfiled item.",
     "file": "bible.html", "find": "    if (sg.id === 'shared') return { seam: { loc: 'shared', mule: null }, filed: mid };",
     "replace": "    if (sg.id === 'shared') return null;", "matches": 1},
    {"why": "A misfiled item's row no longer says which mule it moves FROM.",
     "file": "bible.html", "find": "      if (_fm) return { holder: _fm.name || null, location: 'stash', cell: null, filed: true };",
     "replace": "      if (false) return null;", "matches": 1},
    {"why": "Copies no longer cluster: each copy goes to the first free cell.",
     "file": "bible.html", "find": "var near = it.near || (it.cluster && lastOf[it.n]) || null;",
     "replace": "var near = it.near || null;", "matches": 1},
    {"why": "A saved sibling's cell is ignored: the copy first-fits.",
     "file": "bible.html", "find": "      var near = it.near || (it.cluster && lastOf[it.n]) || null; /* L1 copies of one item cluster */",
     "replace": "      var near = (it.cluster && lastOf[it.n]) || null; /* L1 copies of one item cluster */", "matches": 1},
    {"why": "A sighting of the item anywhere in the target container closes every copy's move (copies merged).",
     "file": "bible.html", "find": "      if (t.kind !== 'throw' && shows(t.to) && here(name, t.to.cell)) {",
     "replace": "      if (t.kind !== 'throw' && shows(t.to) && here(name, null)) {", "matches": 1},
    {"why": "Each copy of a hand add is written onto copy 0's row: copies collapse.",
     "file": "bible.html", "find": "        try { if (typeof _vaultMoveNoteAdded === 'function') _cMv = _vaultMoveNoteAdded(pre.name, _cN - 1); } catch (eMc) {} /* L1 hand copy row */",
     "replace": "        try { if (typeof _vaultMoveNoteAdded === 'function') _cMv = _vaultMoveNoteAdded(pre.name, 0); } catch (eMc) {} /* L1 hand copy row */", "matches": 1},
    {"why": "A hand copy of a misfiled item takes no target cell (no room is treated as in place).",
     "file": "bible.html", "find": "    if (t.manual && t.status === 'to-move' && t.to && t.to.holder != null && t.to.cell == null) return true; /* L1 a hand add always has its row, even with no room */\n",
     "replace": "", "matches": 1},
    {"why": "The task line is ellipsized again: the target is cut off.",
     "file": "bible.html", "find": ".vtk-say{flex:1 1 auto;min-width:0;overflow-wrap:anywhere;white-space:normal}",
     "replace": ".vtk-say{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}", "matches": 1},
    {"why": "The empty dock sends him to VAULT INTEGRITY / Auto-assign again.",
     "file": "bible.html", "find": "[data-misfiled=\"1\"]:empty::after{content:\"nothing loose ✦\"}",
     "replace": "[data-misfiled=\"1\"]:empty::after{content:\"nothing loose — see VAULT INTEGRITY, or press Auto-assign\"}", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
