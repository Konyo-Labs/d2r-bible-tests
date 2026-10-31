# -*- coding: utf-8 -*-
"""REG-3073 (#153.13, GrokBot's vault sweep) - AN UN-OWNED ITEM TAKES ITS COPY RECORDS WITH IT, AND ITS UNDO BRINGS THEM BACK.

GrokBot: "vaultUnown leaves d2r_vaultRecords behind (3 Shako copies -> 3 orphan records)". Measured on the whole page in node:
three hand-added Shakos un-owned -> the name left owned, and all 3 copy rows stayed in d2r_vaultRecords with their moves (to
the shared stash and a WAR mule) until some later rebuild happened to drop them. Those stale rows were also the only reason
the undo brought each copy back where it was. Now every removal of a name (vaultRemove: the un-own, a card X, the last copy's
X) takes the name's copy rows into its removal-journal batch - each copy's move, cell and entry - and drops them from the
store at once; vaultRestoreLast puts them back with the name, so the undo is whole. Driven on the whole page in node.
RED_PROOF below.
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
import vault_page_node as VPN  # noqa: E402

PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n")
BODY = r"""
(function(){
var W = window, DB = W._cbDb(), N = 'Harlequin Crest (Shako)';
function runeId(n){ var r = DB.sk.find(function(s){ return String(s[1] || '').toLowerCase() === (n + ' rune').toLowerCase(); }); return r ? r[0] : null; }
function rows(){ var raw = null; try { raw = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || 'null'); } catch (e) {}
  return ((raw && raw.records) || []).filter(function(r){ return r.name === N; }).sort(function(a, b){ return (a.copyIx | 0) - (b.copyIx | 0); })
    .map(function(r){ return { ix: r.copyIx | 0, to: (r.move && r.move.to) ? (r.move.to.id || r.move.to.holder) : null,
                               runes: (r.entry && r.entry.socketed) ? r.entry.socketed : null }; }); }
/* an Ist Shako and a Ber Shako from the planner (each copy carries its own entry, REG-2844), and a third added by hand */
var SH = DB.it.find(function(x){ return x[1] === 'Harlequin Crest' && x[2] === 'u'; });
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ist')); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3);
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ber')); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3);
W.vaultHandAdd(N, new Date().toISOString(), {}); H.flush(60, 3);
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
W._vaultRecordsPersist(); H.flush(60, 3);
OUT.ist = runeId('Ist'); OUT.ber = runeId('Ber');
OUT.before = { copies: copyCount(N), rows: rows() };
var u = W.vaultUnown(N); H.flush(60, 3);
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
var log = W.vaultRemovalLog(), last = Array.isArray(log) ? log[log.length - 1] : null;
OUT.unowned = { owned: owned.has(N), rows: rows(), carried: (last && Array.isArray(last.records)) ? last.records.filter(function(r){ return r.name === N; }).length : 0 };
W.vaultRestoreLast(); H.flush(60, 3);
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
OUT.back = { owned: owned.has(N), copies: copyCount(N), rows: rows() };
OUT.errors = H.errors.slice(0, 5);
})();
"""


class AnUnownedItemTakesItsCopyRecordsWithIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])
        b = self.o["before"]
        self.assertEqual((b["copies"], len(b["rows"])), (3, 3), "PREMISE: %r" % b)
        self.assertTrue(all(r["to"] for r in b["rows"]), "PREMISE: a copy has no move: %r" % b)
        self.assertEqual([r["runes"] for r in b["rows"]][:2], [[self.o["ist"]], [self.o["ber"]]], "PREMISE: the copies carry no entry: %r" % b)

    def test_the_un_own_leaves_no_copy_record_behind(self):
        u = self.o["unowned"]
        self.assertFalse(u["owned"], u)
        self.assertEqual(u["rows"], [], "the un-owned item's copy records stayed in the store: %r" % u)
        self.assertEqual(u["carried"], 3, "the removal batch does not carry the copies' records: %r" % u)

    def test_the_undo_brings_every_copy_back_whole(self):
        b, before = self.o["back"], self.o["before"]
        self.assertEqual((b["owned"], b["copies"]), (True, 3), b)
        self.assertEqual(b["rows"], before["rows"], "the undo lost a copy's move or entry: %r vs %r" % (b["rows"], before["rows"]))


RED_PROOF = [
    {"why": "REG-3073 - an un-own leaves its copy records in the store",
     "file": "bible.html",
     "find": "            _rSt.records = _rr.records.filter(function(r){ return !(r && removed.indexOf(r.name) >= 0); });\n",
     "replace": "            _rSt.records = _rr.records.slice();\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3073 - the undo leaves the carried records out: each copy comes back without its move and entry",
     "file": "bible.html",
     "find": "          _vrRecGuardedSet(_rbS);\n        }\n      } catch (eRb) {}\n",
     "replace": "        }\n      } catch (eRb) {}\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
