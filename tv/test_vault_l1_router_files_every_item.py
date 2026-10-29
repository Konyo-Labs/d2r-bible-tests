# -*- coding: utf-8 -*-
"""Vault L1 - THE ROUTER FILES EVERY ITEM; MOVE TASKS IS ONE COLLAPSED ROW PER TASK.

Elad, live v3778 (2026-10-21): he hand-added Angelic Sickle, Gheed's Fortune and Hellfire Torch. Angelic Sickle
fell to the UNSORTED DOCK as a discard. His rule: the router files every item; anything in UNSORTED is a routing
bug (his own manual unsort-all stays). And MOVE TASKS drew one big open 'LOCATION NOT SEEN YET' block for one item:
it must be one collapsed row per added item ('<name> ... -> <mule>'), a click expands FROM (MANUAL / source cell)
and TO (that mule, only this item at its exact cell). Driven on the SHIPPED page. NO CHROME = declared skip.
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

import test_vault_l1_a_hand_add_routes_by_type as T  # noqa: E402
H = T.H

HAND = ["Angelic Sickle", "Gheed's Fortune", "Hellfire Torch"]
# set pieces, uniques, magic, charms, runewords - routed (seen, not typed) and typed
ROUTED = ["Tal Rasha's Lidless Eye", "Sigon's Visor", "Angelic Wings", "Harlequin Crest", "Arachnid Mesh",
          "Stone of Jordan", "Annihilus", "Grand Charm", "Small Charm", "Jewel", "Insight", "Enigma", "Spirit"]
TYPED = ["Cathan's Seal", "Isenhart's Horns", "Shako", "War Traveler", "Small Charm", "Grand Charm", "Grief", "Infinity"]

PROBE = (T.READ + r"""
OUT.dock = window._vaultDockNames();
var host = document.getElementById('vault-move-list');
OUT.unseenBlock = host ? host.querySelectorAll('.vmv-group.vmv-unseen').length : -1;
OUT.rows = host ? Array.prototype.map.call(host.querySelectorAll('.vtk-list:not([data-sec="done"]) .vmv-row'), function(r){
  return { name: r.getAttribute('data-name'), copy: +r.getAttribute('data-copy'), kind: r.getAttribute('data-kind'),
           to: r.getAttribute('data-to'), text: r.textContent.replace(/\s+/g, ' ') }; }) : null;
OUT.openAtRest = host ? host.querySelectorAll('.vtk-expand-li').length : -1;
""")

EXPAND = r"""
var host = document.getElementById('vault-move-list'); OUT.x = [];
Array.prototype.forEach.call(host.querySelectorAll('.vtk-list:not([data-sec="done"]) .vmv-row'), function(li){
  var nm = li.getAttribute('data-name'), ci = +li.getAttribute('data-copy');
  var x = window._vaultTaskExpand(nm, ci, li);
  var to = x && x.querySelector('.vtx-to'), from = x && x.querySelector('.vtx-from');
  var items = to ? to.querySelectorAll('[data-key],[data-n],.grid-item,.gi') : [];
  OUT.x.push({ name: nm, copy: ci, from: from && from.getAttribute('data-from'), to: to && to.getAttribute('data-to'),
               rowTo: li.getAttribute('data-to'), toItems: items.length,
               toText: to ? to.textContent : '', open: host.querySelectorAll('.vtk-expand-li').length });
  window._vaultTaskExpand(nm, ci, li);
});
"""


def tearDownModule():
    T.tearDownModule()


def routed_add(names):
    return T.board().run(T.READ + "window._vaultAutoIntakeSet(false);"
                         "%s.forEach(function(n){ try { window._ownedAdd(n, { source: 'screenshot', by: 'test', where: 'a seen frame' }); } catch (e) {} });"
                         "try { persistOwned(); } catch (e) {} try { window.renderVault(); } catch (e) {}" % json.dumps(names))


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class RouterFilesEveryItem(unittest.TestCase):

    def test_v3778_three_hand_adds_none_unsorted_each_a_row(self):
        T.fresh()
        a = T.add_all(HAND)["add"]
        o = T.board().run(PROBE)
        for n in HAND:
            self.assertTrue(a[n]["ok"], "hand door refused %s: %r" % (n, a[n]))
            self.assertNotIn(a[n]["name"], o["dock"], "%s fell to UNSORTED: %r" % (n, o["dock"]))
        sick = [r for r in o["rows"] if r["name"] == a["Angelic Sickle"]["name"]]
        self.assertEqual(len(sick), 1, "Angelic Sickle has %d rows: %r" % (len(sick), o["rows"]))
        self.assertNotEqual(sick[0]["kind"], "throw", "his hand add is a discard row: %r" % sick[0])

    def test_a_hand_add_seen_first_by_a_frame_is_still_filed(self):
        T.fresh()
        a = T.add_all(["Angelic Sickle"])["add"]
        nm = a["Angelic Sickle"]["name"]
        o = T.board().run(T.READ + "var p = JSON.parse(LSR.getItem('d2r_vaultProv') || '{}'); p[%s] = { source: 'screenshot', by: 'reel', where: 'a seen frame' };"
                          "LSR.setItem('d2r_vaultProv', JSON.stringify(p)); window._provParseRaw = null; window._movePackCache = null;"
                          "try { window.renderVault(); } catch (e) {}" % json.dumps(nm) + PROBE)
        self.assertNotIn(nm, o["dock"], "a typed set piece whose first witness was a frame fell to UNSORTED")
        self.assertEqual(len([r for r in o["rows"] if r["name"] == nm and r["kind"] != "throw"]), 1, o["rows"])

    def test_routed_and_typed_items_never_land_in_unsorted(self):
        T.fresh()
        routed_add(ROUTED)
        T.add_all(TYPED)
        o = T.board().run(PROBE)
        self.assertEqual(o["dock"], [], "the router left these in UNSORTED: %r" % o["dock"])

    def test_one_collapsed_row_per_task_expanding_from_and_to(self):
        T.fresh()
        a = T.add_all(HAND + ["Sigon's Visor", "Harlequin Crest", "Insight"])["add"]
        o = T.board().run(PROBE)
        self.assertEqual(o["unseenBlock"], 0, "MOVE TASKS still draws a shared 'Location not seen yet' block")
        self.assertEqual(o["openAtRest"], 0, "a task is open before any click")
        keys = [(r["name"], r["copy"]) for r in o["rows"]]
        self.assertEqual(len(keys), len(set(keys)), "two tasks share a row: %r" % keys)
        x = T.board().run(EXPAND)["x"]
        self.assertTrue(x, "no row expanded")
        for e in x:
            self.assertEqual(e["open"], 1, "expanding %s opened %d panels (merged?)" % (e["name"], e["open"]))
            self.assertIn(e["from"], ("manual", "seen", "demo"), e)
            if e["rowTo"]:
                self.assertEqual(e["to"], e["rowTo"], "TO grid is not this task's cell: %r" % e)
                self.assertLessEqual(e["toItems"], 1, "TO grid of %s draws other items: %r" % (e["name"], e))
                self.assertRegex(e["toText"], r"col \d+ · row \d+", "TO has no exact cell: %r" % e)   # REG-3005 / REG-3062 the one spelling

    def test_distinct_attacks_clear_the_vault_apply_wilson_bar(self):
        from confidence import wilson_lower
        import self_arming as SA
        n = len(RED_PROOF)
        w = wilson_lower(n, n)
        print("vault L1 router files every item: %d distinct attacks, wilson %.4f vs bar %.3f" % (n, w, SA.LOCKS["vault.apply"]["bar"]))
        self.assertGreaterEqual(w, SA.LOCKS["vault.apply"]["bar"])


RED_PROOF = [
    {'why': 'The MANUAL row is not read as proof of his typing, so a frame-seen-first add is unsorted again.', 'file': 'bible.html', 'find': "      return !!(typeof window._vaultManualRow === 'function' && window._vaultManualRow(n));", 'replace': '      return false;', 'matches': 1},
    {'why': "The shared 'Location not seen yet' block comes back over the rows.", 'file': 'bible.html', 'find': '      + \'<ol class="vtk-list" data-sec="moves">\' + moves.map(line).join(\'\') + \'</ol>\';', 'replace': '      + \'<section class="vmv-group vmv-unseen"><ol class="vtk-list" data-sec="moves">\' + moves.map(line).join(\'\') + \'</ol></section>\';', 'matches': 1},
    {'why': 'A click no longer collapses: two panels stay open (tasks pile up).', 'file': 'bible.html', 'find': "    if (open) { open.remove(); li.classList.remove('vtk-open'); return false; }", 'replace': "    if (open && false) { open.remove(); li.classList.remove('vtk-open'); return false; }", 'matches': 1},
    {'why': 'Every task opens on paint (not collapsed).', 'file': 'bible.html', 'find': "      if (host) { host.hidden = false; host.innerHTML = ((typeof _vaultMoveHeldHtml === 'function') ? _vaultMoveHeldHtml() : '') + _vaultMoveHtml(built); }", 'replace': "      if (host) { host.hidden = false; host.innerHTML = ((typeof _vaultMoveHeldHtml === 'function') ? _vaultMoveHeldHtml() : '') + _vaultMoveHtml(built); var _r0 = host.querySelector('ol.vtk-list[data-sec=\"moves\"] li.vtk-line, ol.vtk-list[data-sec=\"throws\"] li.vtk-line'); if (_r0) _vaultTaskExpand(_r0.getAttribute('data-name'), +_r0.getAttribute('data-copy'), _r0); }", 'matches': 1},
    {'why': 'The MANUAL-row proof looks only at copy 1, so a typed copy 0 is not known as his.', 'file': 'bible.html', 'find': "k = String(n) + '\\u0000';", 'replace': "k = String(n) + '\\u00001';", 'matches': 1},
    {'why': "The TO grid names another cell than this task's target.", 'file': 'bible.html', 'find': '\'<div class="vtx-to" data-to="\' + esc(m.task.to.cell) + \'">', 'replace': '\'<div class="vtx-to" data-to="\' + esc((m.task.from && m.task.from.cell) || \'x\') + \'">', 'matches': 1},
    {'why': 'TO drops the exact cell, reading only the mule.', 'file': 'bible.html', 'find': '<div class="vtx-h">TO · \' + esc(m.toSay) + \'</div>\'', 'replace': '<div class="vtx-h">TO · \' + esc(String(m.task.to.holder)) + \'</div>\'', 'matches': 1},
    {'why': "A hand add's FROM is not MANUAL.", 'file': 'bible.html', 'find': 'from = \'<div class="vtx-from" data-from="manual">', 'replace': 'from = \'<div class="vtx-from" data-from="hand">', 'matches': 1},
    {'why': 'The Unsorted Dock takes in filed items too.', 'file': 'bible.html', 'find': "if (_seamD && _seamD.loc === 'loose') {", 'replace': "if (_seamD && (_seamD.loc === 'loose' || _seamD.loc === 'filed')) {", 'matches': 1},
    {'why': "A routed item's mule route is dropped, so uniques/runewords/charms go to the dock.", 'file': 'bible.html', 'find': "return { loc: 'filed', mule: sg.id }; /* v3767 seam route */", 'replace': "return { loc: 'loose', mule: null }; /* v3767 seam route */", 'matches': 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
