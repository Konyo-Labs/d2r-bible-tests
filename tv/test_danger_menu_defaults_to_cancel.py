# -*- coding: utf-8 -*-
"""Vault v2 - the ⚠ Clear & reset menu, and every door in it, defaults to CANCEL; Enter never confirms.

Elad, 2026-10-23, approving the Vault v2 design: the four red buttons left the toolbar for one danger menu, and a
destructive door must never run on a stray Enter. This law presses the doors the way a person does, in Chrome, with
REAL key events (CDP Input.dispatchKeyEvent, so a focused button's own Enter activation is in play too):

  * opening the menu focuses its Cancel, and the rows run mild -> severe;
  * each door's confirm opens with Cancel focused and data-default="cancel";
  * Enter - with focus on Cancel, AND with focus moved onto the red OK - closes the confirm and changes NOTHING
    (owned and every store a door writes - the mule map, journal, receipts - are byte-identical);
  * a deliberate click on OK still runs the door (the positive control, so "nothing changed" is not a dead door);
  * a click outside the menu closes it;
  * a plain uiConfirm (no cancelFirst) still treats Enter as OK - the rule is scoped to the danger doors.

It never presses Escape. NO CHROME = a declared skip. RED_PROOF below. [[regression-guard]]
"""
import json
import os
import sys
import time
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
SHAKO = "Harlequin Crest (Shako)"


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


def key(name, vk):
    t = board().t
    for kind in ("keyDown", "keyUp"):
        p = dict(type=kind, key=name, code=name, windowsVirtualKeyCode=vk, nativeVirtualKeyCode=vk)
        if kind == "keyDown" and name == "Enter":
            p["text"] = "\r"
        if name == " ":
            p["code"] = "Space"
            if kind == "keyDown":
                p["text"] = " "
        t.send("Input.dispatchKeyEvent", **p)
    time.sleep(0.4)


WORLD = ("window._vaultAutoIntakeSet(false); window.switchTab('vault');"
         "var c = document.getElementById('mule-vault-card');"
         "if (c && c.classList.contains('collapsed')) window.toggleCardCollapse('mule-vault-card');"
         "var owned = window.eval('owned'); owned.add('Obedience');"
         "window._ownedProvWrite('Obedience', { source: 'intake-read', by: 'law', holder: 'Chronicle', loc: 'chronicle', scene: 'chronicle', sessionId: 's1', frameId: 'f1', ts: Date.now() });"
         "renderVault();")

# every store a danger door writes (owned, the mule map and hand spots, the vault records/prov/journal/receipts, scan and
# intake history, the removal journal). Derived caches the board rebuilds on its own timers (craftReady, grailFarm, the
# tally, the prov backfill stamp) are not a door's doing and would make "nothing changed" flaky, so they are not read.
STATE = ("var DOOR_KEY = /owned|muleAssign|mulePos|vault|journal|scan|intake|remov|unsort|reset/i;"
         "function snap(){ var o = window.eval('owned'), ls = {};"
         " Object.keys(localStorage).sort().filter(function(k){ return DOOR_KEY.test(k) && !/Backfill$/.test(k); })"
         ".forEach(function(k){ ls[k] = localStorage.getItem(k); });"
         " return JSON.stringify({ owned: Array.from(o).sort(), ls: ls }); }")

# how each door is opened: the row in the menu, or (scan history) the intake strip with a folder connected
DOORS = [
    ("vaultClearUnsorted", "by('#vault-danger-tog').click(); by('#vault-danger-menu [onclick=\"window.vaultClearUnsorted()\"]').click();"),
    ("vaultReset", "by('#vault-danger-tog').click(); by('#vault-danger-menu [onclick=\"window.vaultReset()\"]').click();"),
    ("vaultClearHistory", "by('#vault-danger-tog').click(); by('#vault-danger-menu [onclick=\"window.vaultClearHistory()\"]').click();"),
    ("vaultWipeItems", "by('#vault-danger-tog').click(); by('#vault-danger-menu [onclick=\"window.vaultWipeItems()\"]').click();"),
    ("vaultDropMenuImport", "window._menuAscendingFraction = function(){ return { frac: 1, up: 9, steps: 9, matched: 10 }; };"
                            "window._menuRunNames = function(){ return ['Obedience']; }; renderVault();"
                            "by('#vault-danger-tog').click(); var mb = by('#vault-menuimport-btn'); mb.click();"
                            "by('#vault-danger-tog').click(); by('#vault-danger-tog').click(); mb.click();"),
    ("vaultClearScanHistory", "window._setFolderConnectedUI(true); by('[onclick^=\"window.vaultClearScanHistory(\"]').click();"),
]

H_ = "function by(s){ return document.querySelector(s); }"


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class DangerMenuDefaultsToCancel(unittest.TestCase):

    def setUp(self):
        board().seed({"d2r_owned": [SHAKO], "d2r_muleAssign": {}, "d2r_vaultRecords": None, "d2r_vaultProv": None,
                      "d2r_intakeSeen": {"shot-1.png": 1}})   # a scan slate with one file on it, so its door has work to do
        board().run(WORLD + "OUT.ok = 1;")

    def _open(self, how):
        """press the door, wait for its confirm; returns what the confirm looked like"""
        return board().run(H_ + STATE + "window.__before = snap();" + how +
                           "await new Promise(function(r){ setTimeout(r, 250); });"
                           "var ov = document.querySelector('.ui-confirm-ov'), d = ov && ov.querySelector('.ui-confirm');"
                           "OUT.up = !!ov; OUT.def = d ? d.getAttribute('data-default') : null;"
                           "OUT.focus = document.activeElement ? document.activeElement.className : '';")

    def _after(self):
        return board().run(H_ + STATE + "await new Promise(function(r){ setTimeout(r, 300); });"
                           "OUT.up = !!document.querySelector('.ui-confirm-ov');"
                           "OUT.same = snap() === window.__before; OUT.has = window.eval('owned').has('Obedience');")

    def test_opening_the_menu_focuses_cancel_and_rows_run_mild_to_severe(self):
        o = board().run(H_ + "window.vaultDangerMenuTog(false); by('#vault-danger-tog').click();"
                        "OUT.open = !by('#vault-danger-menu').hidden; OUT.exp = by('#vault-danger-tog').getAttribute('aria-expanded');"
                        "OUT.focus = document.activeElement && document.activeElement.id;"
                        "OUT.order = [].map.call(document.querySelectorAll('#vault-danger-menu .vdm-row [onclick]'), function(b){"
                        "  return (b.getAttribute('onclick').match(/window\\.(\\w+)\\(/) || [])[1]; });"
                        "OUT.role = by('#vault-danger-menu').getAttribute('role');"
                        "window.vaultDangerMenuTog(false);")
        self.assertTrue(o["open"] and o["exp"] == "true", o)
        self.assertEqual(o["focus"], "vault-danger-cancel", "the danger menu does not open on Cancel: %r" % o)
        self.assertEqual(o["role"], "menu")
        # ALT inject run (Elad 2026-10-24 14:09 IDT): the records' clear-history door is the mildest reset (derived, rebuilt at once)
        self.assertEqual(o["order"][:5], ["vaultClearUnsorted", "vaultClearRecords", "vaultReset", "vaultClearHistory", "vaultWipeItems"],
                         "the rows do not run mild -> severe: %r" % o)

    def test_a_click_outside_closes_the_menu(self):
        o = board().run(H_ + "window.vaultDangerMenuTog(false); by('#vault-danger-tog').scrollIntoView({block:'center', behavior:'instant'}); by('#vault-danger-tog').click(); OUT.open = !by('#vault-danger-menu').hidden;"
                        "var r = by('#vault-danger-tog').getBoundingClientRect(); OUT.x = 20; OUT.y = Math.round(r.top + r.height / 2);")
        self.assertTrue(o["open"])
        t = board().t
        for kind in ("mousePressed", "mouseReleased"):
            t.send("Input.dispatchMouseEvent", type=kind, x=o["x"], y=o["y"], button="left", buttons=1 if kind == "mousePressed" else 0, clickCount=1)
        time.sleep(0.3)
        o2 = board().run(H_ + "OUT.open = !by('#vault-danger-menu').hidden; OUT.exp = by('#vault-danger-tog').getAttribute('aria-expanded');")
        self.assertFalse(o2["open"], "a click outside left the danger menu open: %r" % o2)
        self.assertEqual(o2["exp"], "false")

    def test_every_door_opens_on_cancel_and_enter_changes_nothing(self):
        for fn, how in DOORS:
            for on_ok in (False, True):
                board().run(WORLD + "OUT.ok = 1;")
                o = self._open(how)
                self.assertTrue(o["up"], "%s did not ask before acting: %r" % (fn, o))
                self.assertEqual(o["def"], "cancel", "%s's confirm is not marked default=cancel: %r" % (fn, o))
                self.assertIn("ui-confirm-cancel", o["focus"], "%s's confirm does not open with Cancel focused: %r" % (fn, o))
                if on_ok:   # the hard case: he tabbed onto the red button and pressed Enter
                    board().run("document.querySelector('.ui-confirm-ok').focus(); OUT.f = document.activeElement.className;")
                key("Enter", 13)
                a = self._after()
                self.assertFalse(a["up"], "%s: Enter did not close the confirm: %r" % (fn, a))
                self.assertTrue(a["same"] and a["has"], "%s RAN on Enter (focus on %s): %r" % (fn, "OK" if on_ok else "Cancel", a))
            board().run("window.vaultDangerMenuTog(false); window._setFolderConnectedUI(false); OUT.ok = 1;")

    def test_the_chronicle_row_names_its_armed_step(self):
        """Grok review r2 (LOW): after the first press only the button said "Remove N", the row's bold name still read as the unarmed step."""
        o = board().run(H_ + "window._menuAscendingFraction = function(){ return { frac: 1, up: 9, steps: 9, matched: 10 }; };"
                        "window._menuRunNames = function(){ return ['Obedience']; }; renderVault();"
                        "by('#vault-danger-tog').click(); var row = by('#vault-danger-menuimport'), mb = by('#vault-menuimport-btn');"
                        "OUT.shown = !row.hidden; OUT.n0 = row.querySelector('.vdm-name').textContent; mb.click();"
                        "await new Promise(function(r){ setTimeout(r, 200); });"
                        "OUT.b1 = by('#vault-menuimport-btn').textContent; OUT.n1 = by('#vault-danger-menuimport .vdm-name').textContent;"
                        "window.vaultDangerMenuTog(false);")
        self.assertTrue(o["shown"], "PREMISE: the chronicle-page row shows for an alphabetical loose run: %r" % o)
        self.assertEqual(o["n0"], "These look like a chronicle page", o)
        self.assertTrue(o["b1"].startswith("Remove "), "PREMISE: the first press arms the row: %r" % o)
        self.assertEqual(o["n1"], o["b1"], "the row's name still reads as the unarmed step: %r" % o)

    def test_space_on_the_red_ok_changes_nothing(self):
        """Grok review r1 (MEDIUM): Space activates a focused <button> - Tab from Cancel onto OK + Space ran the door."""
        for fn, how in (DOORS[0], DOORS[3]):
            board().run(WORLD + "OUT.ok = 1;")
            o = self._open(how)
            self.assertTrue(o["up"], "%s did not ask: %r" % (fn, o))
            board().run("document.querySelector('.ui-confirm-ok').focus(); OUT.ok = 1;")
            key(" ", 32)
            a = self._after()
            self.assertFalse(a["up"], "%s: Space did not close the confirm: %r" % (fn, a))
            self.assertTrue(a["same"] and a["has"], "%s RAN on Space with the red OK focused: %r" % (fn, a))
            board().run("window.vaultDangerMenuTog(false); OUT.ok = 1;")

    def test_escape_and_tabbing_away_close_the_menu(self):
        """Grok review r1 (LOW): Escape did nothing and Tab out of the zone left the 560px menu open over the page."""
        board().run(H_ + "window.vaultDangerMenuTog(false); by('#vault-danger-tog').click(); OUT.ok = 1;")
        key("Escape", 27)
        o = board().run(H_ + "OUT.open = !by('#vault-danger-menu').hidden; OUT.focus = document.activeElement && document.activeElement.id;"
                        "OUT.exp = by('#vault-danger-tog').getAttribute('aria-expanded');")
        self.assertFalse(o["open"], "Escape left the danger menu open: %r" % o)
        self.assertEqual(o["focus"], "vault-danger-tog", "Escape did not hand focus back to the toggle: %r" % o)
        self.assertEqual(o["exp"], "false")
        o = board().run(H_ + "by('#vault-danger-tog').click(); OUT.open0 = !by('#vault-danger-menu').hidden;"
                        "by('#vault-danger-menu .vdm-name').dispatchEvent(new FocusEvent('focusout', { bubbles: true, relatedTarget: null }));"
                        "OUT.openText = !by('#vault-danger-menu').hidden;"
                        "by('#vault-find-input').focus(); await new Promise(function(r){ setTimeout(r, 100); });"
                        "OUT.openAfter = !by('#vault-danger-menu').hidden; window.vaultDangerMenuTog(false);")
        self.assertTrue(o["open0"] and o["openText"], "a click on plain menu text closed the menu: %r" % o)
        self.assertFalse(o["openAfter"], "focus left the danger zone and the menu stayed open: %r" % o)

    def test_a_deliberate_click_on_ok_still_runs_the_door(self):
        o = self._open(DOORS[0][1])
        self.assertTrue(o["up"], o)
        board().run("document.querySelector('.ui-confirm-ok').click(); OUT.ok = 1;")
        a = self._after()
        self.assertFalse(a["has"], "OK on Delete unsorted did not run - the Enter check above would prove nothing: %r" % a)
        self.assertFalse(a["same"])
        board().run("window.vaultDangerMenuTog(false); OUT.ok = 1;")

    def test_ok_on_clear_scan_history_still_wipes_the_slate(self):
        o = self._open(DOORS[-1][1])
        self.assertTrue(o["up"], o)
        board().run("document.querySelector('.ui-confirm-ok').click(); OUT.ok = 1;")
        a = self._after()
        self.assertFalse(a["same"], "OK on Clear scan history did not wipe the slate - its Enter check proves nothing: %r" % a)
        board().run("window._setFolderConnectedUI(false); OUT.ok = 1;")

    def test_a_plain_confirm_still_takes_enter_as_ok(self):
        board().run("window.__plain = 'pending'; window.uiConfirm('law: plain confirm').then(function(v){ window.__plain = v; });"
                    "await new Promise(function(r){ setTimeout(r, 250); }); OUT.ok = 1;")
        key("Enter", 13)
        o = board().run("OUT.v = window.__plain; OUT.def = !!document.querySelector('.ui-confirm[data-default]');")
        self.assertIs(o["v"], True, "cancelFirst leaked into every uiConfirm: %r" % o)


RED_PROOF = [
    {"why": "Enter confirms again inside a danger door.",
     "file": "bible.html",
     "find": "close(cancelFirst ? false : true); }",
     "replace": "close(true); }",
     "matches": 1},
    {"why": "The danger confirm opens with the red OK focused.",
     "file": "bible.html",
     "find": "ov.querySelector(cancelFirst ? '.ui-confirm-cancel' : '.ui-confirm-ok').focus();",
     "replace": "ov.querySelector('.ui-confirm-ok').focus();",
     "matches": 1},
    {"why": "Reset assignments stops asking for cancelFirst.",
     "file": "bible.html",
     "find": "    if (!(await uiConfirm(_vaultResetConfirm('vaultReset'), {cancelFirst:true, title:'⚠ Danger — Reset assignments'}))) return;",
     "replace": "    if (!(await uiConfirm(_vaultResetConfirm('vaultReset'), {title:'⚠ Danger — Reset assignments'}))) return;",
     "matches": 1},
    {"why": "cancelFirst becomes the default for every confirm (a plain confirm no longer takes Enter).",
     "file": "bible.html",
     "find": "    var cancelFirst = !!opts.cancelFirst;",
     "replace": "    var cancelFirst = true;",
     "matches": 1},
    {"why": "Opening the danger menu no longer focuses its Cancel.",
     "file": "bible.html",
     "find": "      try { var c = document.getElementById('vault-danger-cancel'); if (c) c.focus({ preventScroll: true }); } catch (e2) {}",
     "replace": "",
     "matches": 1},
    {"why": "A click outside the menu no longer closes it.",
     "file": "bible.html",
     "find": "document.addEventListener('mousedown', _vaultDangerOutside, true); document.addEventListener('keydown'",
     "replace": "document.addEventListener('keydown'",
     "matches": 1},
    {"why": "Space on the focused red OK confirms a danger door again (Grok review r1).",
     "file": "bible.html",
     "find": "      else if(cancelFirst && (e.key === ' ' || e.key === 'Spacebar')){ e.preventDefault(); close(false); } }",
     "replace": "      }",
     "matches": 1},
    {"why": "The armed chronicle row keeps its unarmed bold name (Grok review r2).",
     "file": "bible.html",
     "find": "var _mn = _mi.querySelector('.vdm-name'); if (_mn) _mn.textContent = _miTxt;",
     "replace": "",
     "matches": 1},
    {"why": "Escape no longer closes the danger menu.",
     "file": "bible.html",
     "find": "document.addEventListener('keydown', _vaultDangerKey, true);",
     "replace": "",
     "matches": 1},
    {"why": "Focus leaving the danger zone no longer closes the menu.",
     "file": "bible.html",
     "find": "if (z) z.addEventListener('focusout', _vaultDangerLeave);",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
