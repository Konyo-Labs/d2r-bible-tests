# -*- coding: utf-8 -*-
"""Vault v2 - MOVE TASKS is an overlay off a FAB, ⚙ Advanced is a drawer, and the two are never open together.

Elad, 2026-10-23, approving the Vault v2 design: MOVE TASKS no longer takes a right-hand column; it opens from the 📦 FAB
as an overlay that takes no layout room, and the panels that used to sit below the mules live in one ⚙ Advanced drawer.
Opening one closes the other, whichever way it is opened (the FAB, the drawer's summary, an Advanced tab). The toolbar
"+ Add an item" is gone while the planner bar (and its "add by name only →" link) stays. A tick he regrets is taken back
from the line or from the toast. The overlay's open state survives a reload, and the FAB is not drawn off the Vault tab.
Measured in Chrome on the SHIPPED page. NO CHROME = a declared skip. RED_PROOF below. [[regression-guard]]
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

import test_a_sweep_never_reticks_what_he_unticked as H  # noqa: E402

_B = {}
SHAKO = "Harlequin Crest (Shako)"   # screenshot-seen in the stash, routed -> one open move task


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


SEEN = r"""
function seen(el){
  if (!el || !el.isConnected) return false;
  for (var a = el; a; a = a.parentElement){
    if (a.hidden) return false;
    var cs = getComputedStyle(a);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    if (a.tagName === 'DETAILS' && a !== el && !a.open && !(el.closest('summary') && el.closest('details') === a)) return false;
  }
  var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0;
}
function by(s){ return document.querySelector(s); }
function tasksOpen(){ return seen(by('#vault-tasks')); }
function advOpen(){ return !!by('#vault-advanced').open; }
function tick(ms){ return new Promise(function(r){ setTimeout(r, ms || 120); }); }
"""

WORLD = ("window._vaultAutoIntakeSet(false); window.switchTab('vault');"
         "var c = document.getElementById('mule-vault-card');"
         "if (c && c.classList.contains('collapsed')) window.toggleCardCollapse('mule-vault-card');"
         "window._vaultMovePaint(); window.vaultTasksTog(false); by('#vault-advanced').open = false; await tick(150);")


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class MoveTasksAndAdvancedNeverSideBySide(unittest.TestCase):

    def setUp(self):
        board().seed({"d2r_owned": [SHAKO], "d2r_muleAssign": {}, "d2r_vaultRecords": None,
                      "d2r_vaultProv": {SHAKO: {"kind": "owned", "source": "tv", "seen": 2, "looks": [
                          {"session": "w%d" % i, "frame": "f%d" % i, "holder": "MAIN", "loc": "stash", "cell": "c4r0"} for i in range(2)]}}})
        board().run(SEEN + WORLD + "OUT.ok = 1;")

    def test_opening_one_closes_the_other_every_way(self):
        o = board().run(SEEN + "OUT.s = [];"
                        "function st(tag){ OUT.s.push([tag, tasksOpen(), advOpen()]); }"
                        "st('start');"
                        "by('#vault-tasks-fab').click(); await tick(); st('fab');"
                        "by('#vault-advanced > summary').click(); await tick(); st('summary');"
                        "by('#vault-tasks-fab').click(); await tick(); st('fab2');"
                        "by('#vault-advanced .vadv-tab[data-adv=\"ledger\"]') && window.vaultAdvTab('ledger'); await tick(); st('advtab');"
                        "window.vaultTasksTog(true); await tick(); st('tog');"
                        "window.vaultTasksTog(false); await tick(); st('close');")
        s = {r[0]: r[1:] for r in o["s"]}
        self.assertEqual(s["start"], [False, False], o)
        self.assertEqual(s["fab"], [True, False], "the FAB did not open MOVE TASKS alone: %r" % o)
        self.assertEqual(s["summary"], [False, True], "opening Advanced left MOVE TASKS open beside it: %r" % o)
        self.assertEqual(s["fab2"], [True, False], "the FAB left Advanced open beside MOVE TASKS: %r" % o)
        self.assertEqual(s["advtab"], [False, True], "an Advanced tab opened the drawer beside MOVE TASKS: %r" % o)
        self.assertEqual(s["tog"], [True, False], o)
        self.assertEqual(s["close"], [False, False], o)
        self.assertFalse(any(r[1] and r[2] for r in o["s"]), "MOVE TASKS and Advanced were open side by side: %r" % o)

    def test_move_tasks_is_an_overlay_that_takes_no_room(self):
        o = board().run(SEEN + "var m = by('#mule-vault-card .vault-main'), card = by('#mule-vault-card');"
                        "await tick(800); /* the tab's entry animation (gildRise) settles first, so only the overlay can move anything */"
                        "var snap = function(){ var q = m.getBoundingClientRect(); return [q.left, q.top, q.width, q.height, card.getBoundingClientRect().height, document.documentElement.scrollHeight].map(Math.round).join(); };"
                        "for (var w = 0, last = snap(); w < 40; w++) { await tick(100); var nw = snap(); if (nw === last) break; last = nw; } /* under a loaded box the settle can outlast 800ms */"
                        "var r0 = m.getBoundingClientRect(), h0 = card.getBoundingClientRect().height, sh0 = document.documentElement.scrollHeight;"
                        "by('#vault-tasks-fab').click(); await tick(300);"
                        "var r1 = m.getBoundingClientRect(), a = by('#vault-tasks'), p = a.getBoundingClientRect();"
                        "OUT.open = tasksOpen(); OUT.pos = getComputedStyle(a).position; OUT.parent = a.parentElement.tagName;"
                        "OUT.r = [[r0.left, r0.top, r0.width, r0.height], [r1.left, r1.top, r1.width, r1.height]];"
                        "OUT.same = OUT.r[0].map(Math.round).join() === OUT.r[1].map(Math.round).join();"
                        "OUT.card = h0 === card.getBoundingClientRect().height; OUT.sh = sh0 === document.documentElement.scrollHeight;"
                        "OUT.box = [p.left, p.top, p.right, p.bottom, innerWidth, innerHeight];"
                        "var cx = Math.round((p.left + p.right) / 2), cy = Math.round((p.top + p.bottom) / 2), e = document.elementFromPoint(cx, cy);"
                        "OUT.onTop = !!(e && e.closest('#vault-tasks'));"
                        "window.vaultTasksTog(false);")
        self.assertTrue(o["open"], o)
        self.assertEqual(o["pos"], "fixed", "MOVE TASKS is not an overlay: %r" % o)
        self.assertEqual(o["parent"], "BODY", "the overlay is inside the (transformed) tab again - fixed would be fixed to the tab")
        self.assertTrue(o["same"] and o["card"] and o["sh"], "opening MOVE TASKS took layout room: %r" % o)
        b = o["box"]
        self.assertTrue(b[0] >= 0 and b[1] >= 0 and b[2] <= b[4] and b[3] <= b[5], "the overlay is off the screen: %r" % o)
        self.assertTrue(o["onTop"], "the overlay is painted under the page: %r" % o)

    def test_the_toolbar_add_item_is_gone_and_the_planner_bar_stays(self):
        o = board().run(SEEN + "var tb = by('#mule-vault-card .vault-toolbar');"
                        "OUT.tb = !!tb; OUT.addTxt = /\\+\\s*Add an item/.test(tb.textContent);"
                        "OUT.handInTb = !!tb.querySelector('[onclick*=\"vaultHandOpen\"]');"
                        "OUT.planner = seen(by('#vault-planner-q'));"
                        "var l = by('.vault-hand-link'); OUT.link = seen(l) && /add by name only/.test(l.textContent);"
                        "OUT.linkAfterPlanner = !!(l && by('#vault-planner-q').compareDocumentPosition(l) & Node.DOCUMENT_POSITION_FOLLOWING);"
                        "l.click(); await tick(200); OUT.handWin = seen(by('#vault-hand-win .vault-hand-box'));"
                        "if (window.vaultHandClose) window.vaultHandClose(); else { var w = by('#vault-hand-win'); if (w) w.hidden = true; }")
        self.assertTrue(o["tb"], o)
        self.assertFalse(o["addTxt"], "the toolbar still says + Add an item")
        self.assertFalse(o["handInTb"], "the toolbar still opens the hand-add window")
        self.assertTrue(o["planner"], "the planner bar is gone - it must stay")
        self.assertTrue(o["link"] and o["linkAfterPlanner"], "the 'add by name only →' link is not under the planner bar: %r" % o)
        self.assertTrue(o["handWin"], "the link does not open the add-by-name window: %r" % o)

    def test_a_tick_is_undone_from_the_line_and_from_the_toast(self):
        q = ("function openTick(){ return [].slice.call(document.querySelectorAll('#vault-move-list .vtk-list:not([data-sec=done]) [onclick*=\"_vaultTaskTick\"]')).filter(seen)[0]; }"
             "function undoBtn(){ var d = by('#vault-move-list .vtk-donebox'); if (d) d.open = true;"
             "  return [].slice.call(document.querySelectorAll('#vault-move-list .vtk-undo')).filter(seen)[0]; }")
        o = board().run(SEEN + q + "window.vaultTasksTog(true); await tick();"
                        "OUT.n0 = (by('#vault-tasks-n') || {}).textContent; var t = openTick(); OUT.t = !!t; t.click(); await tick();"
                        "OUT.toast = seen(by('#vault-tasks-toast')) && /marked moved/.test(by('#vault-tasks-toast').textContent);"
                        "OUT.n1 = (by('#vault-tasks-n') || {}).textContent;"
                        "var u = undoBtn(); OUT.u = !!u; u.click(); await tick(); OUT.back1 = !!openTick();"
                        "openTick().click(); await tick(); var tu = by('#vault-tasks-toast button'); OUT.tu = seen(tu); tu.click(); await tick();"
                        "OUT.back2 = !!openTick(); OUT.toastGone = !seen(by('#vault-tasks-toast button'));"
                        "window.vaultTasksTog(false);")
        self.assertTrue(o["t"], "no open task to tick: %r" % o)
        self.assertTrue(o["toast"], "a tick says nothing (no toast): %r" % o)
        self.assertNotEqual(o["n0"], o["n1"], "the FAB badge does not count down on a tick: %r" % o)
        self.assertTrue(o["u"] and o["back1"], "the line's Undo does not put the task back: %r" % o)
        self.assertTrue(o["tu"] and o["back2"], "the toast's Undo does not put the task back: %r" % o)

    def test_a_no_room_tick_keeps_its_undo(self):
        """Grok review r1 (MEDIUM): a hand tick on a row with no target cell lost its undo snapshot - _vaultMoveEnsure
        rebuilt the task without it on the next paint - and the row left both the open list and Done."""
        o = board().run("var stored = { name: 'Demon Limb', status: 'moved-manual', manual: true, evidence: [],"
                        " from: { holder: null, location: null, cell: null }, to: { holder: 'SHARED STASH', location: 'shared', cell: null },"
                        " undo: { status: 'to-move', manual: true } };"
                        "var e = window._vaultMoveEnsure('Demon Limb', 0, { map: { 'Demon Limb\\u00000': stored } });"
                        "OUT.fresh = e.fresh; OUT.status = e.task.status; OUT.undo = e.task.undo || null;"
                        "OUT.shown = window._vaultMoveShown(e.task);"
                        "var s2 = Object.assign({}, stored); delete s2.undo; OUT.shownNoUndo = window._vaultMoveShown(s2);")
        self.assertTrue(o["fresh"], "PREMISE: a no-cell row is rebuilt by _vaultMoveEnsure: %r" % o)
        self.assertEqual(o["status"], "moved-manual", o)
        self.assertEqual(o["undo"], {"status": "to-move", "manual": True}, "the rebuild dropped his tick's undo snapshot: %r" % o)
        self.assertTrue(o["shown"], "a ticked no-room row that can be unticked left the list (and Done): %r" % o)
        self.assertFalse(o["shownNoUndo"], "a no-room row with nothing to undo is still hidden as before: %r" % o)

    def test_escape_closes_the_overlay_and_returns_to_the_fab(self):
        board().run(SEEN + "window.vaultTasksTog(true); await tick(); by('#vault-tasks .vtp-x').focus(); OUT.ok = 1;")
        t = board().t
        for kind in ("keyDown", "keyUp"):
            t.send("Input.dispatchKeyEvent", type=kind, key="Escape", code="Escape", windowsVirtualKeyCode=27, nativeVirtualKeyCode=27)
        o = board().run(SEEN + "await tick(200); OUT.open = tasksOpen(); OUT.focus = document.activeElement && document.activeElement.id;"
                        "OUT.exp = by('#vault-tasks-fab').getAttribute('aria-expanded'); window.vaultTasksTog(false);")
        self.assertFalse(o["open"], "Escape inside MOVE TASKS left it open: %r" % o)
        self.assertEqual(o["focus"], "vault-tasks-fab", o)
        self.assertEqual(o["exp"], "false", o)
        # Grok review r2: a click on the FAB leaves focus ON the FAB - Escape there closes it too
        o = board().run(SEEN + "by('#vault-tasks-fab').focus(); by('#vault-tasks-fab').click(); await tick(); OUT.open0 = tasksOpen();"
                        "OUT.f0 = document.activeElement && document.activeElement.id;")
        self.assertTrue(o["open0"] and o["f0"] == "vault-tasks-fab", "PREMISE: the FAB opened MOVE TASKS and kept focus: %r" % o)
        for kind in ("keyDown", "keyUp"):
            t.send("Input.dispatchKeyEvent", type=kind, key="Escape", code="Escape", windowsVirtualKeyCode=27, nativeVirtualKeyCode=27)
        o = board().run(SEEN + "await tick(200); OUT.open = tasksOpen(); window.vaultTasksTog(false);")
        self.assertFalse(o["open"], "Escape with focus on the FAB left MOVE TASKS open: %r" % o)
        # Grok review r3: a mule window opened above the overlay (focus still on the FAB) owns the first Escape
        o = board().run(SEEN + "window.vaultTasksTog(true); await tick(); by('#vault-tasks-fab').focus();"
                        "window.openMuleCard('shared'); await tick(300); var vd = by('#vault-detail'); OUT.win0 = !!(vd && !vd.hidden);"
                        "OUT.open0 = tasksOpen(); OUT.f0 = document.activeElement && document.activeElement.id;")
        self.assertTrue(o["win0"] and o["open0"], "PREMISE: a mule window opened over MOVE TASKS: %r" % o)
        for kind in ("keyDown", "keyUp"):
            t.send("Input.dispatchKeyEvent", type=kind, key="Escape", code="Escape", windowsVirtualKeyCode=27, nativeVirtualKeyCode=27)
        o = board().run(SEEN + "await tick(200); var vd = by('#vault-detail'); OUT.win = !!(vd && !vd.hidden); OUT.open = tasksOpen();"
                        "if (OUT.win) window.vaultCloseCard(true); window.vaultTasksTog(false); if (window.switchTab) window.switchTab('vault');")
        self.assertFalse(o["win"], "Escape on the FAB was eaten by MOVE TASKS - the mule window above it stayed up: %r" % o)
        self.assertTrue(o["open"], "the first Escape closed MOVE TASKS under the mule window: %r" % o)

    def test_the_open_overlay_survives_a_reload(self):
        board().run("window.vaultTasksTog(true); OUT.ok = 1;")
        board().navigate()
        o = board().run(SEEN + "window.switchTab('vault'); await tick(200); OUT.open = tasksOpen();"
                        "window.vaultTasksTog(false);")
        self.assertTrue(o["open"], "MOVE TASKS forgot it was open across a reload")
        board().navigate()
        o = board().run(SEEN + "window.switchTab('vault'); await tick(200); OUT.open = tasksOpen();")
        self.assertFalse(o["open"], "MOVE TASKS reopened after he closed it")

    def test_the_fab_and_overlay_are_not_drawn_off_the_vault_tab(self):
        o = board().run(SEEN + "window.vaultTasksTog(true); await tick(); OUT.on = [seen(by('#vault-tasks-fab')), tasksOpen()];"
                        "window.switchTab('main'); await tick(200); OUT.tab = document.documentElement.getAttribute('data-active-tab'); OUT.off = [seen(by('#vault-tasks-fab')), tasksOpen()];"
                        "window.switchTab('vault'); await tick(200); OUT.back = [seen(by('#vault-tasks-fab')), tasksOpen()];"
                        "window.vaultTasksTog(false);")
        self.assertEqual(o["on"], [True, True], o)
        self.assertEqual(o["off"], [False, False], "the MOVE TASKS FAB/overlay floats over another tab: %r" % o)
        self.assertEqual(o["back"], [True, True], o)


RED_PROOF = [
    {"why": "v3847 - Esc (the contract clicks the x) closes MOVE TASKS and drops focus on <body> instead of the FAB",
     "file": "bible.html",
     "find": "    if (_vtFocusIn && f) { try { f.focus({ preventScroll: true }); } catch (eF) {} }",
     "replace": "", "matches": 1},
    {"why": "The FAB no longer closes Advanced (the two open side by side).",
     "file": "bible.html",
     "find": "    if (want) { var adv = document.getElementById('vault-advanced'); if (adv && adv.open) adv.open = false; } /* never side by side */",
     "replace": "",
     "matches": 1},
    {"why": "Opening Advanced no longer closes MOVE TASKS.",
     "file": "bible.html",
     "find": "if (p && !p.hidden) window.vaultTasksTog(false); } /* never side by side */",
     "replace": "} /* never side by side */",
     "matches": 1},
    {"why": "MOVE TASKS becomes an in-flow panel that takes layout room.",
     "file": "bible.html",
     "find": ".vault-tasks-pop{position:fixed;",
     "replace": ".vault-tasks-pop{position:static;",
     "matches": 1},
    {"why": "The overlay stays inside the transformed tab (fixed becomes fixed-to-the-tab).",
     "file": "bible.html",
     "find": "if (el && document.body && el.parentNode !== document.body) document.body.appendChild(el);",
     "replace": "if (false) document.body.appendChild(el);",
     "matches": 1},
    {"why": "The toolbar's + Add an item comes back.",
     "file": "bible.html",
     "find": "        <button class=\"vault-btn\" onclick=\"window.vaultAddMule()\">➕ Add mule</button>\n",
     "replace": "        <button class=\"vault-btn\" onclick=\"window.vaultHandOpen()\">+ Add an item</button>\n        <button class=\"vault-btn\" onclick=\"window.vaultAddMule()\">➕ Add mule</button>\n",
     "matches": 1},
    {"why": "The toast drops its Undo.",
     "file": "bible.html",
     "find": "    var can = !!(cur && cur.status === 'moved-manual' && cur.undo);",
     "replace": "    var can = false;",
     "matches": 1},
    {"why": "The open state is not restored on reload.",
     "file": "bible.html",
     "find": "      try { if (window.LSR.getItem('vaultTasksOpen') === '1') window.vaultTasksTog(true, true); } catch (e) {}",
     "replace": "",
     "matches": 1},
    {"why": "A no-cell rebuild drops the undo snapshot of his tick (Grok review r1).",
     "file": "bible.html",
     "find": "      undo: stored ? stored.undo : null,   /*",
     "replace": "      undo: null,   /*",
     "matches": 1},
    {"why": "A ticked no-room row leaves the list, so it can never be unticked (Grok review r1).",
     "file": "bible.html",
     "find": "    if (t.status === 'moved-manual' && t.undo && t.to && t.to.holder != null && t.to.cell == null) return true;",
     "replace": "    if (false) return true;",
     "matches": 1},
    {"why": "Escape with focus on the FAB no longer closes MOVE TASKS (Grok review r2).",
     "file": "bible.html",
     "find": "    e.stopImmediatePropagation();\n    top.x.click();\n",
     "replace": "    e.stopImmediatePropagation();\n",
     "matches": 1},
    {"why": "MOVE TASKS steals the Escape of a mule window opened above it (Grok review r3).",
     "file": "bible.html",
     "find": "      if (z >= bz) { bz = z; best = { x: x, box: box }; }\n",
     "replace": "      if (!best) { bz = z; best = { x: x, box: box }; }\n",
     "matches": 1},
    {"why": "Escape inside MOVE TASKS no longer closes it.",
     "file": "bible.html",
     "find": "class=\"vtp-x\" title=\"close MOVE TASKS\" onclick=\"window.vaultTasksTog(false)\"",
     "replace": "class=\"vtp-x\" title=\"close MOVE TASKS\" onclick=\"\"",
     "matches": 1},
    {"why": "The FAB floats over every tab.",
     "file": "bible.html",
     "find": "html:not([data-active-tab=\"vault\"]) .vault-tasks-pop",
     "replace": "html.never-x .vault-tasks-pop",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
