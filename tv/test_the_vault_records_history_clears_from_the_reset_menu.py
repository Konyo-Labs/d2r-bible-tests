# -*- coding: utf-8 -*-
"""ALT inject run 2026-10-24 (bug 1, Elad 14:09 IDT) - THE VAULT RECORDS HAVE A CLEAR-HISTORY DOOR IN THE RESET MENU.

"Besides fixing the delete cleanup, add a clear history option for the vault records by reusing the existing
clear-history pattern ... put it in the reset section and give it a second confirmation like the other resets."
The door is one more entry in window._VAULT_RESET_SCOPE (clears.records, doors.vaultClearRecords), run by the ONE
runner _vaultResetRun with its receipt, worded by _vaultResetConfirm / _vaultResetSay, and listed in the
#vault-danger-menu. Because the records are derived, the runner's own _vaultRecordsRefresh files back every name
a mule still holds: a row a delete left behind goes, nothing held is lost.
RED_PROOF: before this change window.vaultClearRecords is undefined and every test here fails.
"""
import os
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
import json  # noqa: E402
import subprocess  # noqa: E402
import vault_page_node as VPN  # noqa: E402

PRE = r"""
Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });
location.protocol = 'file:'; location.href = 'file:///spec/bible.html'; location.origin = 'null'; location.host = ''; location.hostname = '';
localStorage.setItem('d2r_ownerClaim', '*');
localStorage.setItem('d2r_muleRoster', JSON.stringify([{ id: 'm1', name: 'MULE1' }]));
"""
BODY = r"""
H.flush(60, 3);
window.vaultHandAdd('Harlequin Crest'); H.flush(60, 3);
window._vaultRecordsArm(); H.flush(60, 3);
function recs(){ try { var s = JSON.parse(window.LSR.getItem('d2r_vaultRecords') || 'null'); return s && s.records ? s.records.map(function(r){ return r.name; }) : s; } catch (e) { return 'UNREADABLE'; } }
/* a row a delete left behind, written straight into the store */
var s = JSON.parse(window.LSR.getItem('d2r_vaultRecords'));
var ghost = JSON.parse(JSON.stringify(s.records[0])); ghost.name = 'GBL-TEST-Ghost'; s.records.push(ghost);
window.LSR.setItem('d2r_vaultRecords', JSON.stringify(s));
OUT.before = recs();
var asks = [];
window.uiConfirm = function(m, o){ asks.push({ m: String(m), cancelFirst: !!(o && o.cancelFirst) }); return Promise.resolve(__ANSWERS__[asks.length - 1]); };
(async function(){
await window.vaultClearRecords(); H.flush(60, 3);
OUT.asks = asks; OUT.after = recs();
OUT.door = window._vaultLastReset ? window._vaultLastReset.door : null;
OUT.scope = window._VAULT_RESET_SCOPE.doors.vaultClearRecords;
var rw = document.getElementById('vault-danger-menurecords'); OUT.row = rw ? (document.getElementById('vault-danger-menu').innerHTML || '') : null;
OUT.counted = window._vaultLastReset ? window._vaultLastReset.cleared.records : null;
process.stdout.write('\n__LATE__' + JSON.stringify(OUT) + '\n');
})().catch(function(e){ process.stdout.write('\n__LATE__' + JSON.stringify({ err: String(e && e.stack || e) }) + '\n'); });
"""


def run(answers):
    """the door is async: the body prints its own late line once the reset's promise settles (VPN.run returns
    before it does), so this drives VPN's own program and reads that line"""
    r = subprocess.run([VPN.NODE, "-"], input=VPN.program(BODY.replace("__ANSWERS__", answers), prelude=PRE),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    late = [ln[len("__LATE__"):] for ln in (r.stdout or "").splitlines() if ln.startswith("__LATE__")]
    if len(late) != 1:
        raise AssertionError("the door never settled in node (exit %s): %s" % (r.returncode, (r.stderr or r.stdout)[-2000:]))
    o = json.loads(late[0])
    if "err" in o:
        raise AssertionError("the door threw: %s" % o["err"])
    return o


class TheVaultRecordsHistoryClears(unittest.TestCase):

    def test_two_yeses_clear_the_left_behind_row_and_keep_what_is_held(self):
        o = run("[true, true]")
        self.assertIn("GBL-TEST-Ghost", o["before"], "the seed never planted the left-behind row: %r" % o)
        self.assertEqual(len(o["asks"]), 2, "the door did not ask twice: %r" % o["asks"])
        self.assertTrue(all(a["cancelFirst"] for a in o["asks"]), "a confirm does not open on Cancel: %r" % o["asks"])
        self.assertNotIn("GBL-TEST-Ghost", o["after"], "the left-behind row survived the clear: %r" % o["after"])
        self.assertTrue(any("Harlequin" in n for n in o["after"]), "a held name was lost: %r" % o["after"])
        self.assertEqual(o["door"], "vaultClearRecords", "the clear left no reset receipt")
        self.assertEqual(o["scope"], ["records"])
        self.assertEqual(o["counted"], len(o["before"]), "the receipt does not count the rows it cleared (Grok r1 MED): %r" % o["counted"])

    def test_it_sits_in_the_reset_menu_and_says_its_scope(self):
        """the row is added by the page's script (the menu markup stays as Vault v3 moves it); the order in the real
        browser is held by tv/test_danger_menu_defaults_to_cancel.py"""
        o = run("[false]")
        self.assertIn('onclick="window.vaultClearRecords()"', o["row"] or "", "no Clear records history row in the ⚠ Clear & reset menu")
        self.assertIn('data-scope-for="vaultClearRecords"', o["row"] or "", "the row has no scope line the scope fills")
        self.assertIn("vault records history", o["asks"][0]["m"], "the first confirm does not say what it clears: %r" % o["asks"])

    def test_a_no_at_either_confirm_changes_nothing(self):
        for ans in ("[false]", "[true, false]"):
            o = run(ans)
            self.assertIn("GBL-TEST-Ghost", o["after"], "%s still cleared the records: %r" % (ans, o))

RED_PROOF = [
    {"why": "ALT inject run (bug 1) - the clear-records door stops asking a second time, so one yes clears the history",
     "file": "bible.html",
     "find": "    if (!(await uiConfirm('Are you sure? This is the second confirmation - the vault records history is cleared now.', {cancelFirst:true}))) return;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "ALT inject run (bug 1) - the clear-records door widens past the records: it clears the owned names too, and a held item is lost",
     "file": "bible.html",
     "find": "      vaultClearRecords: Object.freeze(['records'])",
     "replace": "      vaultClearRecords: Object.freeze(['records', 'owned'])",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
