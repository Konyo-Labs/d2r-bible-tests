# -*- coding: utf-8 -*-
"""Vault v3 (Elad t642u, 2026-10-24) - "the searchbar like something there is like in two parts and one works and one
doesnt ... debug that too so its smoother". A box-build click-through of the add row on v3795 found three faults:

  B1  an EMPTY BAR under the add row: #vault-dock-bar is hidden when nothing is loose, but `.vault-dock-bar{display:flex}`
      beat the [hidden] attribute, so an 18px empty frame stayed on screen.
  B2  "add by name only" opened a box with no placeholder (a second empty bar), no focus, Enter added nothing (only a
      mouse click on a row did) and Esc left it open; it and the planner could be open together.
  B3  the ✕ on the ADD AN ITEM bar was dead: the bar never holds text (typing moves into the planner's own box), and
      while the planner is open its overlay covers that ✕.

This law drives the SHIPPED page in Chrome with fixture data. NO CHROME = a declared skip. [[regression-guard]]
"""
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
SHAKO = "Harlequin Crest (Shako)"
SOJ = "The Stone of Jordan"


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


WORLD = ("window._vaultAutoIntakeSet(false); window.switchTab('vault');"
         "var c = document.getElementById('mule-vault-card');"
         "if (c && c.classList.contains('collapsed')) window.toggleCardCollapse('mule-vault-card');"
         "try { window.vaultHandClose(); } catch (e) {} try { window.vaultPlannerClose(); } catch (e) {}"
         "renderVault();")
WAIT = "await new Promise(function(r){ setTimeout(r, 250); });"
KEY = "function key(el, k){ el.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true })); }"
OPEN = "function open(id){ var e = document.getElementById(id); return !!(e && !e.hidden && e.innerHTML); }"


@unittest.skipUnless(os.path.exists(H.RC.CHROME), "no Chrome/Chromium on this machine - UNMEASURED here, not passing")
class VaultAddAndFindDoorsWork(unittest.TestCase):

    def setUp(self):
        board().seed({"d2r_owned": [SHAKO], "d2r_muleAssign": {}, "d2r_vaultRecords": None,
                      "d2r_vaultProv": {SHAKO: {"kind": "owned", "source": "tv", "seen": 2, "looks": [
                          {"session": "w%d" % i, "frame": "f%d" % i, "holder": "MAIN", "loc": "stash", "cell": "c4r0"} for i in range(2)]}}})
        board().run(WORLD + "OUT.ok = 1;")

    def test_b1_nothing_hidden_shows_as_an_empty_bar(self):
        o = board().run("var bar = document.getElementById('vault-dock-bar'); bar.hidden = true;"
                        "OUT.bar = bar.getBoundingClientRect().height;"
                        "OUT.leaks = [].slice.call(document.querySelectorAll('#mule-vault-card [hidden]')).filter(function(e){"
                        "  var r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }).map(function(e){ return e.id || e.className; });")
        self.assertEqual(o["bar"], 0, "the hidden dock bar still takes space: %r" % o)
        self.assertEqual(o["leaks"], [], "a [hidden] element in the Vault is still drawn: %r" % o)

    def test_b3_the_add_bar_has_no_dead_button(self):
        o = board().run("var row = document.querySelector('.vault-planner-find');"
                        "OUT.buttons = row.querySelectorAll('button').length;"
                        "var q = document.getElementById('vault-planner-q'); OUT.ph = q.getAttribute('placeholder') || '';")
        self.assertEqual(o["buttons"], 0, "the ADD AN ITEM bar grew a button that does nothing again: %r" % o)
        self.assertTrue(0 < len(o["ph"]) <= 45, "the planner bar's placeholder is cut off mid-word on screen: %r" % o)

    def test_b2_add_by_name_takes_keys_enter_adds_esc_closes(self):
        o = board().run(KEY + OPEN + "document.querySelector('.vault-hand-link').click();" + WAIT
                        + "var q = document.getElementById('vault-hand-q');"
                        "OUT.focus = document.activeElement === q; OUT.ph = q.getAttribute('placeholder') || '';"
                        "q.value = 'stone of'; window.vaultHandSearch(q.value);" + WAIT
                        + "OUT.before = JSON.parse(window.LSR.getItem('d2r_owned') || '[]').length;"
                        "key(q, 'Enter');" + WAIT
                        + "OUT.partial = JSON.parse(window.LSR.getItem('d2r_owned') || '[]').length;"   # REG-3068 a partial name adds nothing
                        "OUT.partialSay = (document.getElementById('vault-hand-say') || {}).textContent || '';"
                        "q.value = 'the stone of jordan'; window.vaultHandSearch(q.value);" + WAIT
                        + "key(q, 'Enter');" + WAIT
                        + "OUT.owned = JSON.parse(window.LSR.getItem('d2r_owned') || '[]');"
                        "OUT.say = (document.getElementById('vault-hand-say') || {}).textContent || '';"
                        "q.value = 'zzzzqq'; window.vaultHandSearch(q.value); key(q, 'Enter');" + WAIT
                        + "OUT.miss = (document.getElementById('vault-hand-say') || {}).textContent || '';"
                        "OUT.ownedAfterMiss = JSON.parse(window.LSR.getItem('d2r_owned') || '[]').length;"
                        "key(q, 'Escape');" + WAIT + "OUT.openAfterEsc = open('vault-hand-win');")
        self.assertTrue(o["focus"], "the add-by-name box opened without the caret in it: %r" % o)
        self.assertTrue(o["ph"], "the add-by-name box is an empty bar with no words: %r" % o)
        self.assertIn(SOJ, o["owned"], "Enter on the exact name added nothing: %r" % o)
        self.assertEqual(o["partial"], o["before"], "Enter on a partial name ('stone of') added a row by guess (REG-3068): %r" % o)
        self.assertIn("exactly", o["partialSay"], o)
        self.assertIn(SOJ, o["say"])
        self.assertIn("nothing", o["miss"], "Enter on no match said nothing: %r" % o)
        self.assertEqual(o["ownedAfterMiss"], len(o["owned"]), "Enter on no match added something: %r" % o)
        self.assertFalse(o["openAfterEsc"], "Esc left the add-by-name box open")

    def test_b2_one_add_door_at_a_time(self):
        o = board().run(OPEN + "document.querySelector('.vault-hand-link').click();" + WAIT
                        + "OUT.handFirst = open('vault-hand-win');"
                        "window.vaultPlannerOpen('');" + WAIT
                        + "OUT.afterPlanner = [open('vault-hand-win'), open('vault-planner-host')];"
                        "window.vaultHandOpen();" + WAIT
                        + "OUT.afterHand = [open('vault-hand-win'), open('vault-planner-host'), !!window._vaultPlannerOn];"
                        "window.vaultHandClose();")
        self.assertTrue(o["handFirst"])
        self.assertEqual(o["afterPlanner"], [False, True], "the planner opened over an open add-by-name box: %r" % o)
        self.assertEqual(o["afterHand"], [True, False, False], "add-by-name opened over an open planner: %r" % o)

    def test_the_planner_adds_and_find_names_the_mule(self):
        o = board().run("window.vaultPlannerOpen('');" + WAIT
                        + "OUT.open = !!document.getElementById('cb-pick-q') && document.activeElement.id === 'cb-pick-q';"
                        "window.vaultPlannerClose();" + WAIT
                        + "var f = document.getElementById('vault-find-input'); f.value = 'shako'; window.vaultFind('shako');" + WAIT
                        + "var r = document.getElementById('vault-find-results'); OUT.found = !r.hidden && r.textContent;"
                        "document.querySelector('.vault-find-mule .vault-find-x').click();" + WAIT
                        + "OUT.cleared = [f.value, r.hidden];")
        self.assertTrue(o["open"], "focusing ADD AN ITEM did not open the planner with the caret in its box: %r" % o)
        self.assertIn("Harlequin Crest", o["found"] or "", "Find on a mule did not name the item: %r" % o)
        self.assertEqual(o["cleared"], ["", True], "the Find ✕ did not clear: %r" % o)


# Observed RED on the pre-fix build (a note, not a tamper list):
RED_OBSERVED = """on 27b9a028 (v3795): b1 leaks ['vault-dock-bar']; b3 buttons 1; b2 focus False, ph '', SoJ not owned after
Enter, Esc leaves it open; one-door afterPlanner [True, True]"""

if __name__ == "__main__":
    unittest.main()
