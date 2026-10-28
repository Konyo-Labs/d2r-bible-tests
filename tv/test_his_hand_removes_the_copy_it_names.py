# -*- coding: utf-8 -*-
"""#154 P3c (REG-2849) - HIS HAND REMOVES THE COPY IT NAMES, AND THE OTHER COPIES KEEP WHAT MAKES THEM THEMSELVES.

Each copy carries its own entry (REG-2844), but no door could take out ONE named copy. The count stepper took the LAST copy
off, so with an Ist Shako (copy 1) and a Ber Shako (copy 2) he could not remove the Ist one: the Ber record went, and the
Ist entry stayed under the copy that was left. Measured on the whole page in node. The trade door (REG-2877) already
removed THAT copy, with the copies after it closing up, and that is the mechanism reused here; there is no second one.
window.vaultRemoveCopy(name, copyIx) goes through window._vaultTradeEvent as 'remove-copy'. The copy's record (its move and
its own entry) leaves in a removal-journal batch on his ✕'s lane, with no trade slot and no traded row. The copies after
it close up, the count drops one, and the toolbar Undo is named for that copy. vaultRestoreLast puts it back where it was.
The last copy leaves through vaultRemove as his ✕. The opened MOVE row of each copy carries the button. RED_PROOF below.
"""
import json
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
import vault_page_node as VPN  # noqa: E402

PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n")
BODY = r"""
(function(){
var W = window, DB = W._cbDb(), N = 'Harlequin Crest (Shako)';
function runeId(n){ var r = DB.sk.find(function(s){ return String(s[1] || '').toLowerCase() === (n + ' rune').toLowerCase(); }); return r ? r[0] : null; }
function ents(){ var raw = null; try { raw = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || 'null'); } catch (e) {}
  return ((raw && raw.records) || []).filter(function(r){ return r.name === N; }).sort(function(a, b){ return (a.copyIx | 0) - (b.copyIx | 0); })
    .map(function(r){ return [r.copyIx | 0, r.entry ? (r.entry.socketed || []) : null, !!r.trade]; }); }
function traded(){ var raw = null; try { raw = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || 'null'); } catch (e) {} return ((raw && raw.tradedOut) || []).length; }
var SH = DB.it.find(function(x){ return x[1] === 'Harlequin Crest' && x[2] === 'u'; });
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ist')); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3);
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ber')); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3);
OUT.ist = runeId('Ist'); OUT.ber = runeId('Ber');
OUT.before = { copies: copyCount(N), ents: ents() };
/* the opened MOVE row of copy 1 carries the button */
var hx = W._vaultTaskExpandHtml(N, 0);
OUT.button = /class="vault-btn vtx-remove"[^>]*window\.vaultRemoveCopy\('Harlequin Crest \(Shako\)',0\)/.test(hx);
var r = W.vaultRemoveCopy(N, 0); H.flush(60, 3);
var log = W.vaultRemovalLog(), last = Array.isArray(log) ? log[log.length - 1] : null;
OUT.removed = { ok: r && r.ok, why: r && r.why, copies: copyCount(N), owned: owned.has(N), ents: ents(), traded: traded(),
                lane: last && last.lane, outEnt: last && last.copyOut && last.copyOut.row && last.copyOut.row.entry ? last.copyOut.row.entry.socketed : null,
                undo: (W._vaultUndo && W._vaultUndo.what) || null };
W.vaultRestoreLast(); H.flush(60, 3);
OUT.back = { copies: copyCount(N), ents: ents() };
/* the last copy leaves as his ✕ */
W.vaultRemoveCopy(N, 1); H.flush(60, 3);
var r2 = W.vaultRemoveCopy(N, 0); H.flush(60, 3);
OUT.last = { ok: r2 && r2.ok, owned: owned.has(N), noted: Object.keys(JSON.parse(W.LSR.getItem('d2r_vaultRemovedAt') || '{}')) };
OUT.noIx = W.vaultRemoveCopy('Harlequin Crest (Shako)');
OUT.errors = H.errors.slice();
})();
"""


class HisHandRemovesTheCopyItNames(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted_and_he_has_two_shakos_told_apart(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])
        b = self.o["before"]
        self.assertEqual(b, {"copies": 2, "ents": [[0, [self.o["ist"]], False], [1, [self.o["ber"]], False]]}, "PREMISE: %r" % b)

    def test_the_opened_row_carries_the_button(self):
        self.assertTrue(self.o["button"], "copy 1's opened MOVE row has no remove-this-copy button")

    def test_removing_the_ist_copy_keeps_the_ber_copy(self):
        r = self.o["removed"]
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["copies"], r["owned"]), (1, True), r)
        self.assertEqual(r["ents"], [[0, [self.o["ber"]], False]], "the copy left was not the Ber Shako: %r" % r)
        self.assertEqual((r["lane"], r["outEnt"]), ("card-click", [self.o["ist"]]), "the journal batch is not his X on the Ist copy: %r" % r)
        self.assertEqual(r["traded"], 0, "a hand removal wrote a traded row: %r" % r)
        self.assertEqual(r["undo"], "the removal of copy 1 of Harlequin Crest (Shako)", r)

    def test_the_undo_puts_it_back_where_it_was(self):
        self.assertEqual(self.o["back"], self.o["before"], self.o["back"])

    def test_the_last_copy_leaves_as_his_x(self):
        l = self.o["last"]
        self.assertEqual((l["ok"], l["owned"]), (True, False), l)
        self.assertIn("harlequin crest", [k.lower() for k in l["noted"]], l)

    def test_a_removal_names_its_copy(self):
        self.assertFalse(self.o["noIx"]["ok"], self.o["noIx"])


RED_PROOF = [
    {"why": "REG-2849 - the trade door refuses his hand's removal of a copy",
     "file": "bible.html",
     "find": "    if (['listed', 'unlisted', 'trade-out', 'trade-in', 'remove-copy'].indexOf(kind) < 0)",
     "replace": "    if (['listed', 'unlisted', 'trade-out', 'trade-in'].indexOf(kind) < 0)",
     "matches": 1, "needs": "node"},
    {"why": "REG-2849 - a hand removal is journaled as a trade-out",
     "file": "bible.html",
     "find": "    var _lane = (kind === 'remove-copy') ? 'card-click' : 'trade-out';\n",
     "replace": "    var _lane = 'trade-out';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2849 - a hand removal writes a traded row the D2JSP card would count",
     "file": "bible.html",
     "find": "    var _tWith = function(st){ if (kind !== 'trade-out') return null;",
     "replace": "    var _tWith = function(st){",
     "matches": 1, "needs": "node"},
    {"why": "REG-2849 - the opened MOVE row has no button for the copy",
     "file": "bible.html",
     "find": "      + ' onclick=\"event.stopPropagation();window.vaultRemoveCopy(\\'' + jsArg(m.name) + '\\',' + (m.copyIx | 0) + ')\">✕ Remove this copy</button>'\n",
     "replace": "      + '>✕ Remove this copy</button>'\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2849 - the Undo chip calls a hand removal a trade-out",
     "file": "bible.html",
     "find": "    var _undoWhat = (kind === 'remove-copy') ? ('the removal of copy ' + (k + 1) + ' of ' + nm) : ('the trade-out of ' + nm);   /* REG-2849 */\n",
     "replace": "    var _undoWhat = 'the trade-out of ' + nm;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
