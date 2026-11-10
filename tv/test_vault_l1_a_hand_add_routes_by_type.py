# -*- coding: utf-8 -*-
"""Vault L1 — a hand add routes by its type, reads MANUAL to its target cell, and opens BEFORE | AFTER.

Elad, 2026-10-19: "the manual version of it is me adding item by item and just making sure all items are
properly being routed to the right mules/stashed/throwout" - "jewels too" - "the demonstration there from manual on
the left and the right side should still be like the visual rendering ... with the cross reference".

Driven on the SHIPPED page through the real door (window.vaultHandAdd) with AUTO INTAKE off:
  - a set piece, a unique, a runeword, a grand charm, a jewel and an amulet each get ONE auto move row,
    FROM = MANUAL (no cell), TO = the mule its type routes to, at a real cell;
  - each footprint is the game's (2x3 armor, 2x2 helm, 2x4 polearm, 1x3 grand charm, 1x1 jewel / amulet, 2x1 belt);
  - placement is append-only: a later, larger add never lands on a cell already given (ruling 1);
  - a first real sighting upgrades the SAME row to a real FROM cell (ruling 4);
  - an item seen on the equipment is locked: no move row; seen off the character again, it is routed (ruling 8);
  - clicking the row opens BEFORE (MANUAL badge, or the real grid once seen) and AFTER (the organized grid with the
    item at its target), real art in real cells, the same ring on both, one instruction line, and it closes cleanly.
NO CHROME AT ALL = a declared skip, never a pass. RED_PROOF below. [[regression-guard]] [[heart-first]]
"""
import json
import re
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_a_sweep_never_reticks_what_he_unticked as H  # noqa: E402  (its Board drives the shipped page)

_B = {}

# typed name -> (type, the name the vault files it under, expected mule holder, footprint w x h)
BY_TYPE = [
    ("set", "Tal Rasha's Guardianship", "Tal Rasha's Guardianship (armor)", "SETS-TAL-IK", (2, 3)),
    ("unique", "Harlequin Crest", "Harlequin Crest (Shako)", "SHARED STASH", (2, 2)),
    ("runeword", "Insight", "Insight", "RUNEWORDS", (2, 4)),
    # REG-2993 - his 2026-10-28 ruling (REG-2895): "no gheeds no... MF no... those go to charms mmule dedicated" - Gheed's
    # Fortune is muled on the dedicated CHARMS mule, which supersedes REG-2859's UNI-SMALL (his 2026-10-15 ruling)
    ("charm", "Gheed's Fortune", "Gheed's Fortune", "CHARMS", (1, 3)),
    ("jewel", "Rainbow Facet", "Rainbow Facet", "SHARED STASH", (1, 1)),
    ("amulet", "Nokozan Relic", "Nokozan Relic", "UNI-SMALL", (1, 1)),
    ("belt", "Arachnid Mesh", "Arachnid Mesh", "SHARED STASH", (2, 1)),
    ("war runeword", "Enigma", "Enigma", "SHARED STASH", (2, 3)),
]

READ = r"""
function recs(){ try { return (JSON.parse(LSR.getItem('d2r_vaultRecords') || '{}').records || []); } catch (e) { return []; } }
function moveOf(nm){ return recs().filter(function(r){ return r.name === nm && r.move; }).map(function(r){ return r.move; }); }
"""


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


def fresh():
    board().seed({"d2r_owned": [], "d2r_vaultProv": {}, "d2r_muleAssign": {}, "d2r_vaultRecords": None})


def add_all(names):
    return board().run(READ + "window._vaultAutoIntakeSet(false); OUT.add = {};"
                       "%s.forEach(function(n){ var a = window.vaultHandAdd(n); OUT.add[n] = { ok: a && a.ok, name: a && a.name, why: a && a.why }; });"
                       % json.dumps(names))


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class AHandAddRoutesByType(unittest.TestCase):

    def test_each_type_gets_one_manual_row_to_its_mule_at_a_real_cell(self):
        fresh()
        typed = [t[1] for t in BY_TYPE]
        add_all(typed)
        o = board().run(READ + "OUT.m = {}; %s.forEach(function(n){ OUT.m[n] = moveOf(n); });"
                        "var host = document.getElementById('vault-move-list');"
                        "OUT.rows = host ? Array.prototype.map.call(host.querySelectorAll('.vmv-row'), function(r){"
                        "  return { name: r.getAttribute('data-name'), manual: !!r.querySelector('.vmv-manual-badge'), text: r.textContent }; }) : [];"
                        % json.dumps([t[2] for t in BY_TYPE]))
        for kind, _typed, nm, holder, _fp in BY_TYPE:
            mv = o["m"][nm]
            self.assertEqual(len(mv), 1, "%s (%s) has %d move rows, not one: %r" % (nm, kind, len(mv), mv))
            mv = mv[0]
            self.assertTrue(mv["manual"], "%s (%s) is not a MANUAL row: %r" % (nm, kind, mv))
            self.assertIsNone(mv["from"]["cell"], "%s (%s) invented a FROM cell: %r" % (nm, kind, mv))
            self.assertEqual(mv["to"]["holder"], holder, "%s (%s) routed to the wrong mule: %r" % (nm, kind, mv))
            self.assertRegex(mv["to"]["cell"] or "", r"^(stash|shared|inventory):c\d+r\d+$", "%s (%s) has no target cell" % (nm, kind))
            row = [r for r in o["rows"] if r["name"] == nm]
            self.assertEqual(len(row), 1, "%s does not paint exactly one row: %r" % (nm, row))
            self.assertTrue(row[0]["manual"], "%s row does not wear the MANUAL badge: %r" % (nm, row))
            self.assertIn(holder, row[0]["text"])

    def test_each_type_packs_at_the_game_footprint(self):
        o = board().run("OUT.c = {}; %s.forEach(function(n){ OUT.c[n] = window._itemCells(n); });" % json.dumps([t[2] for t in BY_TYPE]))
        for kind, _t, nm, _h, fp in BY_TYPE:
            c = o["c"][nm]
            self.assertEqual((c["w"], c["h"]), fp, "%s (%s) footprint %r, the game's is %r" % (nm, kind, c, fp))
            self.assertFalse(c.get("approx"), "%s (%s) footprint is a guess: %r" % (nm, kind, c))

    def test_placement_is_append_only_and_no_two_targets_overlap(self):
        fresh()
        add_all(["Harlequin Crest"])
        first = board().run(READ + "OUT.c = moveOf('Harlequin Crest (Shako)')[0].to.cell;")["c"]
        add_all(["Annihilus"])
        nxt = board().run(READ + "OUT.c = moveOf('Annihilus')[0].to.cell;")["c"]
        self.assertEqual(nxt, "shared:c2r0", "the next add did not take the next free cell beside Shako: %r" % nxt)
        add_all(["Enigma", "Rainbow Facet", "Arachnid Mesh", "Insight", "Spirit"])
        o = board().run(READ + "OUT.r = recs().filter(function(r){ return r.move && r.move.to && r.move.to.cell; }).map(function(r){"
                        " var s = window.vaultSize(r.name); return [r.name, r.move.to.holder, r.move.to.cell, s[0], s[1]]; });")
        shako = [r for r in o["r"] if r[0] == "Harlequin Crest (Shako)"]
        self.assertEqual(shako[0][2], first, "a later add moved the cell Shako was already given: %r -> %r" % (first, shako))
        import re
        rects = []
        for nm, holder, cell, w, h in o["r"]:
            m = re.match(r"^(\w+):c(\d+)r(\d+)$", cell)
            rects.append((nm, holder, m.group(1), (int(m.group(2)), int(m.group(3)), w, h)))
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a[1] == b[1] and a[2] == b[2]:
                    self.assertFalse(overlap(a[3], b[3]), "%s and %s were sent to overlapping cells: %r %r" % (a[0], b[0], a, b))

    def test_a_first_sighting_upgrades_the_same_row_to_a_real_from_cell(self):
        fresh()
        add_all(["Insight"])
        o = board().run(READ + "var before = moveOf('Insight')[0]; window._vaultAutoIntakeSet(true);"
                        "OUT.ap = window._vaultMoveApplySight('Insight', { holder: 'MULE-3', location: 'stash', cell: 'stash:c4r2', frame: 'f_1' });"
                        "OUT.mv = moveOf('Insight'); OUT.before = before;"
                        "var row = document.querySelector('#vault-move-list .vmv-row[data-name=\"Insight\"]');"
                        "OUT.badge = !!(row && row.querySelector('.vmv-manual-badge')); OUT.text = row ? row.textContent : null;"
                        "OUT.nrows = document.querySelectorAll('#vault-move-list .vmv-row[data-name=\"Insight\"]').length;")
        self.assertTrue(o["ap"]["applied"], o)
        self.assertEqual(len(o["mv"]), 1, "the sighting made a second row: %r" % o["mv"])
        mv = o["mv"][0]
        self.assertEqual(mv["from"]["cell"], "stash:c4r2", "the row did not take the real FROM cell: %r" % mv)
        self.assertEqual(mv["from"]["holder"], "MULE-3")
        self.assertEqual(mv["to"], o["before"]["to"], "the sighting changed the target: %r" % mv)
        self.assertEqual(mv["status"], "to-move", mv)
        self.assertIn("f_1", mv["evidence"], mv)
        self.assertEqual(o["nrows"], 1)
        self.assertFalse(o["badge"], "the upgraded row still wears MANUAL")
        self.assertIn("MULE-3", o["text"])

    def test_an_equipped_item_gets_no_row_and_is_routed_once_seen_off_the_character(self):
        fresh()
        add_all(["Insight"])
        o = board().run(READ + "window._vaultAutoIntakeSet(true);"
                        "window._vaultMoveApplySight('Insight', { holder: 'MAIN', location: 'equipment', cell: 'equipment:c0r0', frame: 'e_1' });"
                        "OUT.worn = document.querySelectorAll('#vault-move-list .vmv-row[data-name=\"Insight\"]').length;"
                        "OUT.wornMv = moveOf('Insight')[0];"
                        "window._vaultMoveApplySight('Insight', { holder: 'MAIN', location: 'stash', cell: 'stash:c1r1', frame: 'e_2' });"
                        "OUT.off = document.querySelectorAll('#vault-move-list .vmv-row[data-name=\"Insight\"]').length;"
                        "OUT.offMv = moveOf('Insight')[0];")
        self.assertEqual(o["worn"], 0, "an equipped item got a move row: %r" % o["wornMv"])
        self.assertEqual(o["off"], 1, "seen off the character, it was not routed: %r" % o["offMv"])
        self.assertEqual(o["offMv"]["from"]["cell"], "stash:c1r1", o["offMv"])
        self.assertEqual(o["offMv"]["status"], "to-move", o["offMv"])

    def test_each_move_task_is_its_own_collapsed_row_that_expands_its_own_from_and_to(self):
        """Elad 2026-10-20 22:35: every MOVE TASK is its own collapsed row; a click expands THAT row: FROM = MANUAL (by
        hand) / the screenshot's source cell / a DEMO grid that says it is simulated; TO = a mini grid of that exact mule
        with ONLY this item at its exact cell. One grid per task - never a shared 'TO SETS-REST' grid of several tasks."""
        fresh()
        # v3845 - heart2 found this BLIND: two tasks on two mules both at c0r0, so a merged TO grid and a grid drawn at
        # the mule's first cell looked identical. A ring now shares Nokozan's mule at a cell that is not c0r0.
        add_all(["Gheed's Fortune", "Nokozan Relic", "Nagelring"])
        q = ("function px(e){ return [parseInt(e.style.left, 10), parseInt(e.style.top, 10)]; }"
             "function ex(n){ var r = document.querySelector('#vault-move-list .vmv-row[data-name=\\\"' + n + '\\\"]'); var x = r && r.nextElementSibling;"
             " if (!x || !x.classList.contains('vtk-expand-li')) return null; var t = x.querySelector('.vtx-to');"
             " return { from: x.querySelector('.vtx-from').getAttribute('data-from'), manual: !!x.querySelector('.vtx-from .vmv-manual-badge'),"
             "  fromItems: x.querySelectorAll('.vtx-from .vd-item').length, fromPx: x.querySelector('.vtx-from .vd-item') ? px(x.querySelector('.vtx-from .vd-item')) : null,"
             "  to: t.getAttribute('data-to'), items: Array.prototype.map.call(t.querySelectorAll('.vd-item'), function(e){ return e.getAttribute('title') || ''; }),"
             "  px: t.querySelector('.vd-item') ? px(t.querySelector('.vd-item')) : null, grids: x.querySelectorAll('.vd-grid').length, art: t.querySelectorAll('.vd-item img, .vd-item [class*=art]').length }; }")
        o = board().run(READ + q + "OUT.collapsed = document.querySelectorAll('#vault-move-list .vtk-expand-li').length;"
                        "var a = document.querySelector('#vault-move-list .vmv-row[data-name=\\\"Nokozan Relic\\\"]'); a.click();"
                        "document.querySelector('#vault-move-list .vmv-row[data-name=\\\"Gheed\\'s Fortune\\\"]').click();"
                        "document.querySelector('#vault-move-list .vmv-row[data-name=\\\"Nagelring\\\"]').click();"
                        "OUT.k = ex(\"Nagelring\"); OUT.toK = moveOf(\"Nagelring\")[0].to;"
                        "OUT.toNh = moveOf('Nokozan Relic')[0].to;"
                        "OUT.n = ex('Nokozan Relic'); OUT.g = ex(\"Gheed's Fortune\"); OUT.open = document.querySelectorAll('#vault-move-list .vtk-expand-li').length;"
                        "OUT.toN = moveOf('Nokozan Relic')[0].to.cell; OUT.toG = moveOf(\"Gheed's Fortune\")[0].to.cell;"
                        "a.click(); OUT.after = ex('Nokozan Relic'); OUT.gStill = !!ex(\"Gheed's Fortune\");"
                        "window._vaultAutoIntakeSet(true);"
                        "window._vaultMoveApplySight('Nokozan Relic', { holder: 'MULE-2', location: 'stash', cell: 'stash:c3r1', frame: 'n_1' });"
                        "document.querySelector('#vault-move-list .vmv-row[data-name=\\\"Nokozan Relic\\\"]').click(); OUT.seen = ex('Nokozan Relic');"
                        "var d = document.createElement('div'); d.innerHTML = window._vaultTaskExpandHtml('Nokozan Relic', 0); OUT.demoFn = typeof window._vaultTaskExpandHtml;")
        self.assertEqual(o["collapsed"], 0, "a task row starts expanded")
        # #144.14 (REG-2780): the merged BEFORE | AFTER popup is removed from the page, so "a row click opened it" can no longer
        # happen here; tv/test_a_move_row_expands_inline_and_the_popup_is_gone.py holds the popup gone and the expand drawn.
        self.assertEqual(o["open"], 3, "three clicked tasks are not three expansions: %r" % o["open"])
        self.assertEqual(o["toK"].get("holder"), o["toNh"].get("holder"),
                         "PREMISE: the two small uniques do not share one mule, so a merged TO grid is unexercised: %r %r" % (o["toK"], o["toNh"]))
        self.assertNotEqual(o["toK"]["cell"], o["toN"], "PREMISE: two tasks on one mule share one cell")
        self.assertTrue(any(not c.endswith("c0r0") for c in (o["toK"]["cell"], o["toN"])),
                        "PREMISE: every task sits at c0r0, so 'drawn at its exact cell' is unexercised")
        for k, nm, to in (("n", "Nokozan Relic", o["toN"]), ("g", "Gheed", o["toG"]), ("k", "Nagelring", o["toK"]["cell"])):
            e = o[k]
            self.assertTrue(e, "%s did not expand" % nm)
            self.assertEqual(e["from"], "manual"); self.assertTrue(e["manual"])
            self.assertEqual(e["to"], to, "%s TO is not its own target cell" % nm)
            self.assertEqual(len(e["items"]), 1, "%s TO grid holds other tasks: %r" % (nm, e["items"]))
            self.assertIn(nm, e["items"][0])
            self.assertGreaterEqual(e["art"], 1, "TO tile carries no art")
            m = re.match(r"^\w+:c(\d+)r(\d+)$", to)
            self.assertEqual(e["px"], [3 + int(m.group(1)) * 28, 3 + int(m.group(2)) * 28], "%s is not drawn at its exact cell" % nm)
        self.assertIsNone(o["after"], "a second click did not collapse the row")
        self.assertTrue(o["gStill"], "collapsing one task closed another")
        s = o["seen"]
        self.assertEqual(s["from"], "seen", s); self.assertEqual(s["fromItems"], 1, s)
        self.assertEqual(s["fromPx"], [3 + 3 * 28, 3 + 1 * 28], "FROM is not the screenshot's source cell: %r" % s)

    def test_a_hand_typed_base_routes_to_the_bases_mule_at_its_footprint(self):
        fresh()
        bases = [("Monarch", (2, 3)), ("Archon Plate", (2, 3)), ("Eth Thresher", (2, 4)), ("Ethereal Archon Plate", (2, 3))]
        a = add_all([b for b, _ in bases])["add"]
        o = board().run(READ + "OUT.m = {}; OUT.c = {}; %s.forEach(function(n){ OUT.m[n] = moveOf(n); OUT.c[n] = window.vaultSize(n); });"
                        "OUT.rows = document.querySelectorAll('#vault-move-list .vmv-row .vmv-manual-badge').length;"
                        % json.dumps([b for b, _ in bases]))
        import re
        rects = []
        for nm, fp in bases:
            self.assertTrue(a[nm]["ok"], "the hand door refused the base %s: %r" % (nm, a[nm]))
            mv = o["m"][nm]
            self.assertEqual(len(mv), 1, "%s has %d rows: %r" % (nm, len(mv), mv))
            self.assertTrue(mv[0]["manual"] and mv[0]["from"]["cell"] is None, mv)
            self.assertEqual(mv[0]["to"]["holder"], "SOCKETED", "%s did not route to the bases mule: %r" % (nm, mv))
            self.assertEqual(tuple(o["c"][nm]), fp, "%s footprint %r" % (nm, o["c"][nm]))
            m = re.match(r"^stash:c(\d+)r(\d+)$", mv[0]["to"]["cell"])
            rects.append((nm, (int(m.group(1)), int(m.group(2)), fp[0], fp[1])))
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                self.assertFalse(overlap(rects[i][1], rects[j][1]), "bases overlap: %r" % rects)
        self.assertEqual(o["rows"], len(bases))

    def test_a_hand_typed_base_changes_no_other_list(self):
        # a base owned through any OTHER door (no hand receipt) stays exactly where it was: not in records, not in the pool
        board().seed({"d2r_owned": ["Monarch", "Insight"], "d2r_vaultProv": {}, "d2r_muleAssign": {}, "d2r_vaultRecords": None})
        o = board().run("var rn = function(){ return (window._vaultRecords().records || []).map(function(r){ return r.name; }).sort(); };"
                        "OUT.pool0 = ownedPool(); OUT.dock0 = window._vaultDockNames(); OUT.rec0 = rn(); OUT.hb0 = window._vaultHandBasePool();"
                        "window._vaultAutoIntakeSet(false); OUT.add = window.vaultHandAdd('Archon Plate');"
                        "OUT.pool1 = ownedPool(); OUT.dock1 = window._vaultDockNames(); OUT.rec1 = rn(); OUT.hb1 = window._vaultHandBasePool();")
        self.assertTrue(o["add"]["ok"], o["add"])
        self.assertEqual(o["hb0"], [], "a base he never typed counted as hand-typed: %r" % o["hb0"])
        self.assertNotIn("Monarch", o["rec0"], "a non-hand base entered the records: %r" % o["rec0"])
        self.assertEqual(o["pool0"], o["pool1"], "ownedPool changed")
        self.assertEqual(o["dock0"], o["dock1"], "the dock changed")
        self.assertEqual(o["hb1"], ["Archon Plate"], o["hb1"])
        self.assertEqual(sorted(set(o["rec1"]) - set(o["rec0"])), ["Archon Plate"], "records changed beyond the typed base: %r -> %r" % (o["rec0"], o["rec1"]))
        self.assertTrue(set(o["rec0"]) <= set(o["rec1"]))

    def test_a_catalogue_name_without_the_or_in_another_case_is_that_item(self):
        fresh()
        a = add_all(["Stone of Jordan", "stone of jordan", "THE STONE OF JORDAN"])["add"]
        for typed in ("Stone of Jordan", "stone of jordan", "THE STONE OF JORDAN"):
            self.assertTrue(a[typed]["ok"], "%r was refused: %r" % (typed, a[typed]))
            self.assertEqual(a[typed]["name"], "The Stone of Jordan", a[typed])
        o = board().run(READ + "OUT.m = moveOf('The Stone of Jordan'); OUT.bad = moveOf('Stone of Jordan').length;"
                        "OUT.junk = window.vaultHandAdd('Stone of Nothing');")
        # L1 (Elad 2026-10-20): a name he types again is ANOTHER COPY. Three spellings resolve to the ONE catalogue
        # item (no row under a variant name), and as three hand adds they are three copies: three rows, three cells.
        self.assertEqual(len(o["m"]), 3, "three hand adds of one item are three copies: %r" % o["m"])
        self.assertEqual(len(set(m["to"]["cell"] for m in o["m"])), 3, "the copies share a cell: %r" % o["m"])
        self.assertEqual(set(m["to"]["holder"] for m in o["m"]), {"SHARED STASH"}, o["m"])
        self.assertEqual(o["bad"], 0)
        self.assertFalse(o["junk"]["ok"], "an alias invented an item: %r" % o["junk"])

    def test_no_add_a_move_control_exists_anywhere(self):
        fresh()
        add_all(["Insight"])
        o = board().run("try { switchTab('vault'); } catch (e) {} await new Promise(function(r){ setTimeout(r, 500); });"
                        "OUT.n = Array.prototype.filter.call(document.querySelectorAll('button,input,[role=button],[contenteditable]'), function(e){"
                        " var t = (e.textContent || '') + ' ' + (e.placeholder || '') + ' ' + (e.getAttribute('aria-label') || '') + ' ' + (e.getAttribute('onclick') || '') + ' ' + (e.getAttribute('oninput') || '');"
                        " return /add a move|type an item, or select one|_vaultMoveAdd/i.test(t); }).map(function(e){ return e.outerHTML.slice(0, 120); });"
                        "OUT.q = !!document.getElementById('vault-move-q'); OUT.fn = typeof window._vaultMoveAddNamed + typeof window._vaultMoveAddOpen;"
                        "OUT.inList = document.querySelectorAll('#vault-move-list input:not([type=checkbox])').length;")
        self.assertEqual(o["n"], [], "an add-a-move control is on the page: %r" % o["n"])
        self.assertFalse(o["q"])
        self.assertEqual(o["fn"], "undefinedundefined")
        self.assertEqual(o["inList"], 0, "the move list carries an input (a search there may only filter, never add)")

    def test_find_on_a_mule_lists_a_hand_add_with_its_mule_and_cell(self):
        fresh()
        add_all(["Arcanna's Sign", "Insight"])
        o = board().run(READ + "try { switchTab('vault'); } catch (e) {} await new Promise(function(r){ setTimeout(r, 500); });"
                        "var i = document.getElementById('vault-find-input'); i.value = 'arcan'; i.dispatchEvent(new Event('input', { bubbles: true })); await new Promise(function(r){ setTimeout(r, 900); });"
                        "var res = document.getElementById('vault-find-results'); OUT.hidden = res.hidden; OUT.text = res.textContent;"
                        "OUT.to = moveOf(\"Arcanna's Sign (amulet)\").map(function(m){ return m.to.cell; });"
                        # REG-3013 - FIND says the target in its own words since REG-2884 ("Mule 1 · Personal stash · col 1 ·
                        # row 1"), never the raw "stash:c0r0": the page's own cell resolver gives the col and row it must name
                        "OUT.at = OUT.to.map(function(c){ var a = window._vaultCellAt ? window._vaultCellAt(c) : null;"
                        "  return a ? ('col ' + (a.x + 1) + ' \u00b7 row ' + (a.y + 1)) : null; });")
        self.assertFalse(o["hidden"], "typing in FIND ON A MULE showed nothing")
        self.assertIn("Arcanna's Sign", o["text"])
        self.assertIn("SETS-REST", o["text"], o["text"])
        self.assertTrue(o["to"] and o["at"] and o["at"][0], "PREMISE: the move target did not resolve to a cell: %r" % o)
        self.assertIn(o["at"][0], o["text"], "FIND does not name the cell: %r / %r" % (o["text"], o["to"]))
        self.assertNotIn("cell UNKNOWN", o["text"])

    def test_a_hand_added_unruled_set_piece_gets_a_manual_row_not_throw_out(self):
        fresh()
        add_all(["Arcanna's Sign"])
        o = board().run(READ + "OUT.m = moveOf(\"Arcanna's Sign (amulet)\"); OUT.dock = window._vaultDockNames();"
                        "var l = document.getElementById('vault-move-list'); OUT.text = l.textContent;"
                        "OUT.badge = !!l.querySelector('.vmv-row .vmv-manual-badge');"
                        "OUT.ctl = window.suggestMule(\"Arcanna's Sign (amulet)\").id;"
                        "OUT.line = window.vaultProposeLine(\"Arcanna's Sign (amulet)\");")
        self.assertNotIn("throw-out advice", o["line"], "the organizer still advises throw-out for his hand add: %r" % o["line"])
        self.assertIn("SETS-REST", o["line"], o["line"])
        self.assertEqual(o["ctl"], "__throwout", "premise: the rules still default it to throw-out")
        self.assertEqual(len(o["m"]), 1, o)
        self.assertEqual(o["m"][0]["to"]["holder"], "SETS-REST", o["m"])
        self.assertTrue(o["badge"])
        self.assertNotIn("Arcanna's Sign (amulet)", o["dock"], "the hand add still sits in Unsorted")
        self.assertNotIn("Nothing is out of place", o["text"])

    def test_the_list_never_says_nothing_while_a_hand_add_waits(self):
        fresh()
        # a hand receipt for a name the router cannot home: no target cell can exist
        board().seed({"d2r_owned": ["Insight"], "d2r_muleAssign": {}, "d2r_vaultRecords": None,
                      "d2r_vaultProv": {"Insight": {"kind": "owned", "source": "hand", "by": "+ Add an item",
                                                    "where": "the Vault (+ Add an item)", "at": "2026-10-19T18:00:00.000Z", "looks": [], "seen": 0}},
                      "d2r_mulesRoster": None})
        o = board().run("var b = window._vaultMoveCollect ? null : null; window._movePackCache = null;"
                        "var built = { tasks: [], groups: [], locks: [], unrouted: ['Insight'] };"
                        "OUT.html = window._vaultMoveHtml(built); OUT.empty = window._vaultMoveHtml({ tasks: [], groups: [], locks: [] });")
        self.assertNotIn("Nothing is out of place", o["html"])
        self.assertIn("added by hand with no target cell yet", o["html"])
        self.assertIn("Insight", o["html"])
        self.assertIn("Nothing is out of place", o["empty"], "the control: an empty list with no hand adds")

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import confluence, wilson_lower
        import self_arming as SA
        bar = SA.LOCKS["vault.apply"]["bar"]
        kinds_bar = SA.LOCKS["vault.apply"]["kinds_bar"]
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        conf = confluence(["sabotage"], SA.KINDS)
        msg = ("vault L1 hand add: %d distinct attacks, wilson %.4f vs vault.apply bar %.3f; "
               "kinds sabotage %.2f vs %.2f" % (n, w, bar, conf, kinds_bar))
        print(msg)
        self.assertGreaterEqual(w, bar, msg)
        self.assertLess(conf, kinds_bar, msg)



class TheEquippedLockIsOneRuleAskedWithoutAWindow(unittest.TestCase):
    """REG-2722 - an equipped item is locked by ONE rule (_vaultMoveMainLane), asked here in node.

    The equipped lock used to live in three places (_vaultMoveAutoRow's own copy, _vaultMoveMainLane, and a _vaultMoveWorn
    line under it), so red-proof [26] attacked one and the others held: BLIND at two v3818 pushes. It is one rule now, and
    this case asks it directly, so the proof is seen red here without a window."""

    def ask(self, lane):
        from cb_node_harness import NODE
        import test_an_auto_sighting_joins_the_manual_move as _A   # its _fn cutter: one copy, not a second [[copy-drift]]
        if NODE is None:
            raise AssertionError("node is not on this machine - this case does not skip")
        with open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        js = "\n".join(["var window = globalThis;", "window._laneLocked = function(){ return false; };",
                        "window._standingKit = function(){ return true; };",
                        "function _vaultMoveHome(){ return { id: 'uni-armor' }; }",
                        _A._fn(src, "_vaultMoveFarmLoot"), _A._fn(src, "_vaultMoveMainLane"), _A._fn(src, "_vaultMoveAutoRow"),
                        "process.stdout.write(JSON.stringify({ lock: _vaultMoveMainLane(%s, 'Insight'), "
                        "auto: _vaultMoveAutoRow('Insight', { lane: %s }) }));" % (json.dumps(lane), json.dumps(lane))])
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise AssertionError("the shipped lane rule would not run in node: %s" % r.stderr[-400:])
        return json.loads(r.stdout)

    def test_an_equipped_item_is_locked_by_the_one_rule_and_a_stashed_one_is_not(self):
        for lane in ("equipment", "equipped"):
            o = self.ask(lane)
            self.assertTrue(o["lock"], "%s is not a locked lane" % lane)
            self.assertEqual(o["auto"], {"row": False, "why": "main"}, "%s: the auto row offered a move" % lane)
        self.assertFalse(self.ask("stash")["lock"], "a stashed item is locked as if worn")

RED_PROOF = [
    {"why": "The TO mini grid draws every task bound for that mule again (the merged 'TO SETS-REST' grid).",
     "file": "bible.html", "find": "      var it = [{ n: m.name, key: m.name + '#' + m.copyIx, x: c.x, y: c.y, w: sz[0], h: sz[1] }];",
     "replace": "      var it = (label === 'To' ? (function(){ var bag = _vaultMoveBag(), all = []; Object.keys(bag.map || {}).forEach(function(k){ var mv = bag.map[k], cm = mv && mv.to && String(mv.to.cell || '').match(/^(\\w+):c(\\d+)r(\\d+)$/); if (cm && String(mv.to.holder || '') === String(m.task.to.holder || '')) all.push({ n: k.split(String.fromCharCode(0))[0], key: k, x: +cm[2], y: +cm[3], w: 1, h: 1 }); }); return all; })() : [{ n: m.name, key: m.name + '#' + m.copyIx, x: c.x, y: c.y, w: sz[0], h: sz[1] }]);", "matches": 1},
    {"why": "The task is drawn at the mule's first cell, not its exact cell.",
     "file": "bible.html", "find": "      : m.to ? '<div class=\"vtx-to\" data-to=\"' + esc(m.task.to.cell) + '\"><div class=\"vtx-h\">TO · ' + esc(m.toSay) + '</div>' + one(m.to, m.dims.to, 'To', 'task-to') + '</div>'",
     "replace": "      : m.to ? '<div class=\"vtx-to\" data-to=\"' + esc(m.task.to.cell) + '\"><div class=\"vtx-h\">TO · ' + esc(m.toSay) + '</div>' + one({ x: 0, y: 0 }, m.dims.to, 'To', 'task-to') + '</div>'", "matches": 1},
    {"why": "A second click does not collapse the row.",
     "file": "bible.html", "find": "    if (open) { open.remove(); li.classList.remove('vtk-open'); return false; }",
     "replace": "    if (false) { open.remove(); }", "matches": 1},
    {"why": "FROM of a screenshot-seen task falls back to the MANUAL badge.",
     "file": "bible.html", "find": "    else if (m.from) from = ", "replace": "    else if (false) from = ", "matches": 1},
    {"why": "A hand-typed task shows a grid instead of MANUAL.",
     "file": "bible.html", "find": "    if (m.manual && m.task && m.task.manual) from = ", "replace": "    if (false) from = ", "matches": 1},
    {"why": "Expanding one task collapses every other open task (one shared panel).",
     "file": "bible.html", "find": "    var x = document.createElement('li'); x.className = 'vtk-expand-li';",
     "replace": "    [].slice.call(document.querySelectorAll('.vtk-expand-li')).forEach(function(e){ e.remove(); }); var x = document.createElement('li'); x.className = 'vtk-expand-li';", "matches": 1},
    {"why": "The organizer line still advises throw-out for a hand-kept set piece.",
     "file": "bible.html",
     "find": "      if (_hm) return { ok: true, moved: false, kind: 'mule', id: _hs.mule,",
     "replace": "      if (false) return { ok: true, moved: false, kind: 'mule', id: _hs.mule,",
     "matches": 1},
    {"why": "An ADD A MOVE button comes back in the move list header.",
     "file": "bible.html",
     "find": "+ '<span class=\"vmv-locks\">' + locks + '</span></div>'; /* v3773 no manual move */",
     "replace": "+ '<span class=\"vmv-locks\">' + locks + '</span><button type=\"button\">Add a move</button></div>'; /* v3773 no manual move */",
     "matches": 1},
    # v3864 - 'FIND keeps cell UNKNOWN for a hand add the move list already placed' moved to the node law
    # test_a_find_row_opens_every_mule_page_its_copies_sit_on (FindSaysAHandAddIsHisMoveToItsTarget): since REG-2884 FIND's
    # own 'would' answer names the cell too, so this browser case stayed green under it (BLIND on ci/proof-keys-v3864).
    {"why": "A hand-typed unruled set piece goes back to throw-out advice in Unsorted.",
     "file": "bible.html",
     "find": "        return { loc: 'filed', mule: 'sets-rest' }; /* L1 he typed a set piece: kept, not thrown out */",
     "replace": "        return { loc: 'loose', mule: null }; /* L1 he typed a set piece: kept, not thrown out */",
     "matches": 1},
    {"why": "The list says Nothing is out of place while a hand add has no target.",
     "file": "bible.html",
     "find": "    if (!moves.length && !throws.length && !unr.length) html += '<p class=\"vmv-empty\">Nothing is out of place.</p>';",
     "replace": "    if (!moves.length && !throws.length) html = head + '<p class=\"vmv-empty\">Nothing is out of place.</p>';",
     "matches": 1},
    {"why": "The hand door no longer tries the alias, so Stone of Jordan is refused.",
     "file": "bible.html",
     "find": "if (!_vaultKeeps(r.name)) { var al = _vhAlias(r.name); if (al && _vaultKeeps(al)) r = { ok: true, name: al }; } /* L1 alias */",
     "replace": "/* L1 alias */",
     "matches": 1},
    {"why": "The alias keeps a leading The, so Stone of Jordan matches nothing.",
     "file": "bible.html",
     "find": ".replace(/^the\\s+/, '');",
     "replace": ";",
     "matches": 1},
    {"why": "The alias is case-sensitive, so a lower-case name matches nothing.",
     "file": "bible.html",
     "find": "function k(x){ return String(x == null ? '' : x).trim().toLowerCase()",
     "replace": "function k(x){ return String(x == null ? '' : x).trim()",
     "matches": 1},
    {"why": "The hand door refuses a catalogue base again.",
     "file": "bible.html",
     "find": "if (!_vaultKeeps(r.name) && !_vaultHandBase(r.name) && !_vaultHandRolled(r.name)) /* L1 a catalogue base passes the hand door */",
     "replace": "if (!_vaultKeeps(r.name)) /* L1 a catalogue base passes the hand door */",
     "matches": 1},
    {"why": "An ethereal base is not recognised as its catalogue base.",
     "file": "bible.html",
     # REG-2703 (#154.18) moved the quality peel into _VH_QUAL, beside Superior; the tamper drops the ethereal words from it
     "find": "  var _VH_QUAL = /^(eth|ethereal|superior)\\s+/i;\n",
     "replace": "  var _VH_QUAL = /^(superior)\\s+/i;\n",
     "matches": 1},
    {"why": "The packer leaves hand-typed bases out, so they get no target cell.",
     "file": "bible.html",
     "find": "try { if (typeof window._vaultHandBasePool === 'function') pool = pool.concat(window._vaultHandBasePool()); } catch (eHb) {} /* L1 hand bases pack */",
     "replace": "/* L1 hand bases pack */",
     "matches": 1},
    {"why": "The records leave hand-typed bases out, so the row is never saved.",
     "file": "bible.html",
     "find": "try { if (typeof window._vaultHandBasePool === 'function') poolAll = poolAll.concat(window._vaultHandBasePool()); } catch (eHb) {} /* L1 hand bases record */",
     "replace": "/* L1 hand bases record */",
     "matches": 1},
    {"why": "Any owned base counts as hand-typed, so a base from another door enters the records.",
     "file": "bible.html",
     "find": "if (_vaultHandTyped(n)) out.push(n); /* L1 hand-typed base */",
     "replace": "out.push(n); /* L1 hand-typed base */",
     "matches": 1},
    {"why": "Saved targets are not reserved, so a later bigger add is packed onto the cell Shako was given.",
     "file": "bible.html",
     "find": "    }); /* L1 append-only occ */",
     "replace": "    }); kept = {}; occBy = {}; /* L1 append-only occ */",
     "matches": 1},
    {"why": "The saved cell is dropped from the pack, so the item is re-packed.",
     "file": "bible.html",
     "find": "if (kept[n + '\\u0000' + i]) continue; /* L1 saved cell stays */",
     "replace": "/* L1 saved cell stays */",
     "matches": 1},
    {"why": "The stash grid ignores the taken rectangles.",
     "file": "bible.html",
     "find": "), 10, 10, occOn('stash', 10));",
     "replace": "), 10, 10);",
     "matches": 1},
    {"why": "The shared grid ignores the taken rectangles.",
     "file": "bible.html",
     "find": "        var pk = packGrid(leftP, 10, 10, occP);",
     "replace": "        var pk = packGrid(leftP, 10, 10);",
     "matches": 1},
    {"why": "A sighting no longer upgrades the MANUAL row, so it reads moved-elsewhere with no FROM cell.",
     "file": "bible.html",
     "find": "if (t.manual && t.status === 'to-move' && !atTo && (t.from == null",
     "replace": "if (false && t.manual && t.status === 'to-move' && !atTo && (t.from == null",
     "matches": 1},
    {"why": "The upgrade writes a fresh target, so the sighting moves where he was sent.",
     "file": "bible.html",
     "find": "var up = _vaultMoveTask({ name: name, from: place, to: t.to, status: 'to-move', evidence: ev0, manual: true, opened: t.opened, seen: t.seen }); /* L1 sighting upgrades the manual row */",
     "replace": "var up = _vaultMoveTask({ name: name, from: place, to: place, status: 'to-move', evidence: ev0, manual: true, opened: t.opened, seen: t.seen }); /* L1 sighting upgrades the manual row */",
     "matches": 1},
    {"why": "The sighting frame is not kept as the upgrade's proof.",
     "file": "bible.html",
     "find": "if (sighting.frame != null && sighting.frame !== '' && ev0.indexOf(String(sighting.frame)) < 0) ev0.push(String(sighting.frame));",
     "replace": "void ev0;",
     "matches": 1},
    {"why": "An equipped item gets a move row.",
     "file": "bible.html",
     "find": "    if (!main[lane]) return false;\n    return !(lane === 'inventory' && _vaultMoveFarmLoot(name));",
     "replace": "    if (!main[lane] || lane === 'equipment' || lane === 'equipped') return false;\n    return !(lane === 'inventory' && _vaultMoveFarmLoot(name));",
     "matches": 1},
    {"why": "An item seen worn stays locked after it is seen off the character.",
     "file": "bible.html",
     "find": "(t.from == null || t.from.cell == null || _vaultMoveWorn(t.from))",
     "replace": "(t.from == null || t.from.cell == null)",
     "matches": 1},
    {"why": "Clicking a row opens the evidence panel, not BEFORE | AFTER.",
     "file": "bible.html",
     "find": "        + ' onclick=\"window._vaultTaskExpand(\\'' + nm + '\\',' + ci + ',this)\">'",
     "replace": "        + ' onclick=\"window._vaultEvidenceOpen(\\'' + nm + '\\')\">'",
     "matches": 1},
    {"why": "A seen (upgraded) row stays the MANUAL badge instead of its real FROM cell.",
     "file": "bible.html",
     "find": "(manual ? '<b class=\"vmv-manual-badge\">MANUAL</b>'",
     "replace": "(true ? '<b class=\"vmv-manual-badge\">MANUAL</b>'",
     "matches": 1},
    {"why": "REG-2993 - Gheed's Fortune goes back to UNI-SMALL (REG-2859's answer), not the CHARMS mule his 2026-10-28 ruling names.",
     "file": "bible.html",
     "find": "    return k.mf ? { id: CHARM_MULE, why: 'Gheed\u2019s Fortune, a magic-find charm \u2014 the CHARMS mule' + RULE }",
     "replace": "    return k.mf ? { id: 'uni-small', why: 'Gheed\u2019s Fortune, a magic-find charm \u2014 the CHARMS mule' + RULE }",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
