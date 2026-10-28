# -*- coding: utf-8 -*-
"""#154 P3c (REG-2848) - A SIGHTING JOINS ITS COPY: BY ITS CELL, AND BY ITS MODS WHEN IT CARRIES THEM.

His plan is to add his items by hand now and let AUTO's sightings join those same records later. Measured on the whole page
in node:
  * a filed item's later reads added NO look to its witness row (the filing took its looks once). A Stone of Jordan added
    by hand, filed on a read at stash c0r0 and then read at c2r0 still counted 1 copy, and its MOVE row said copy 0
    "moved-elsewhere";
  * two Griffon's Eyes added by hand, then one of them read at c5r0: the count became the cells (1), so the second copy's
    record and its MOVE row were dropped;
  * a sighting at a new cell went to the first unseen hand copy whatever it was. An Ist Shako and a Ber Shako could not
    be told apart (REG-2844 gave each copy its own entry).
Now:
  * a read of a filed item joins its looks, so a second cell is the second copy (v3767, his Q1) and copy 0 stays where it
    was read;
  * the looks cap never drops the only look of a cell;
  * the copies his hand typed (each has its MANUAL row) are never counted below the cells;
  * a sighting that carries mods joins the unseen hand copy whose own entry it matches.
RED_PROOF below.
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
           "localStorage.setItem('d2r_ownerClaim', '*'); localStorage.setItem('d2r_vaultAutoIntake', 'on');\n")
HELP = r"""
var W = window, DB = W._cbDb(), T0 = Date.now();
function recs(n){ var raw = null; try { raw = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || 'null'); } catch (e) {}
  return ((raw && raw.records) || []).filter(function(r){ return r.name === n; }).map(function(r){ var m = r.move || {};
    return { ix: r.copyIx, from: m.from ? m.from.cell : null, status: m.status || null, manual: !!m.manual }; }).sort(function(a, b){ return a.ix - b.ix; }); }
function cells(n){ var p = null; try { p = JSON.parse(W.LSR.getItem('d2r_vaultProv') || '{}')[n] || {}; } catch (e) {}
  var s = {}; (p.looks || []).forEach(function(l){ if (l && l.cell) s[JSON.stringify(l.cell)] = 1; }); return Object.keys(s).length; }
function see(reg, n, x, a, b, extra){ var cell = { x: x, y: 0, container: 'stash' }, at = new Date(T0 + 60000).toISOString();
  var w = { by: 'tv-register', lane: 'stash', loc: 'stash', scene: 'stash', holder: 'MULE1', at: at, cell: cell,
    sessions: [{ session: a, frame: a + '_f', lane: 'stash', conf: 0.9, cell: cell, holder: 'MULE1', at: at }] };
  if (b) w.sessions.push({ session: b, frame: b + '_f', lane: 'stash', conf: 0.9, cell: cell, holder: 'MULE1', at: at });
  for (var k in (extra || {})) w[k] = extra[k];
  var r = W.tvVaultRegister(reg, w); H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3); return r && (r.mode || r.refused); }
"""
BODY = HELP + r"""
(function(){
/* A - a filed item read at a new cell */
var J = 'The Stone of Jordan';
W.vaultHandAdd(J, new Date().toISOString(), {}); H.flush(60, 3);
see(J, J, 0, 'b1', 'b2');
OUT.a0 = { recs: recs(J), cells: cells(J) };
see(J, J, 2, 'b3', 'b4');
OUT.a1 = { recs: recs(J), cells: cells(J), span: W._vaultPresenceSpan(J, copyCount(J)) };
/* B - fourteen more reads of c0r0 never push c2r0's look out */
for (var i = 0; i < 14; i++) see(J, J, 0, 'r' + i);
OUT.b = { cells: cells(J), recs: recs(J).length };
/* C - two hand copies, one of them read: both stay */
var G = "Griffon's Eye";
W.vaultHandAdd(G, new Date().toISOString(), {}); H.flush(60, 3); W.vaultHandAdd(G, new Date().toISOString(), {}); H.flush(60, 3);
see(G, G, 5, 'g1', 'g2');
OUT.c = { recs: recs(G), span: W._vaultPresenceSpan(G, copyCount(G)) };
/* D - an Ist Shako and a Ber Shako by hand; a sighting carrying the Ber mods joins the Ber copy */
function runeId(n){ var r = DB.sk.find(function(s){ return String(s[1] || '').toLowerCase() === (n + ' rune').toLowerCase(); }); return r ? r[0] : null; }
var SH = DB.it.find(function(x){ return x[1] === 'Harlequin Crest' && x[2] === 'u'; }), N = 'Harlequin Crest (Shako)';
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ist')); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3);
W.vaultPlannerOpen(''); W._cbChoose(SH[0]); W._cbEdit('sockets', '1'); W._cbSocket(0, runeId('Ber')); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3);
var ber = JSON.parse(JSON.stringify(W._vaultCopyEntry(N, 1) || null));
OUT.d0 = { copies: copyCount(N), ber: ber && ber.socketed };
see('Harlequin Crest', N, 6, 'h1', 'h2', { entry: ber });
OUT.d = recs(N);
OUT.errors = H.errors.slice(0, 5);
})();
"""


class ASightingJoinsItsCopyByCellAndByMods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])

    def test_a_new_cell_of_a_filed_item_is_its_second_copy_not_copy_0_moving(self):
        a0, a1 = self.o["a0"], self.o["a1"]
        self.assertEqual((a0["cells"], [r["from"] for r in a0["recs"]]), (1, ["stash:c0r0"]), "PREMISE: %r" % a0)
        self.assertEqual(a1["cells"], 2, "the read at a new cell never reached the filing's looks: %r" % a1)
        self.assertEqual([(r["ix"], r["from"]) for r in a1["recs"]], [(0, "stash:c0r0"), (1, "stash:c2r0")], a1)
        self.assertNotEqual(a1["recs"][0]["status"], "moved-elsewhere", "copy 0 was read as moved elsewhere: %r" % a1)

    def test_the_looks_cap_never_drops_the_only_look_of_a_cell(self):
        self.assertEqual(self.o["b"], {"cells": 2, "recs": 2}, "fourteen reads of one cell pushed the other copy's cell out: %r" % self.o["b"])

    def test_his_hand_copies_are_never_counted_below_the_cells(self):
        c = self.o["c"]
        self.assertEqual((c["span"], [r["ix"] for r in c["recs"]]), (2, [0, 1]), "a hand copy vanished once its twin was read: %r" % c)

    def test_a_sighting_with_mods_joins_the_copy_whose_mods_match(self):
        d0, d = self.o["d0"], self.o["d"]
        self.assertEqual(d0["copies"], 2, "PREMISE: %r" % d0)
        self.assertTrue(d0["ber"], "PREMISE: the Ber copy has no entry: %r" % d0)
        by = {r["ix"]: r["from"] for r in d}
        self.assertEqual((by.get(0), by.get(1)), (None, "stash:c6r0"), "the Ber sighting joined the wrong copy: %r" % d)


RED_PROOF = [
    {"why": "REG-2848 - a read of a filed item adds no look to its filing again",
     "file": "bible.html",
     "find": "        if (lkF && lkF.frame && !lsF.some(function(l){ return l && l.frame === lkF.frame; })){\n",
     "replace": "        if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2848 - the looks cap drops the oldest look whatever cell it holds",
     "file": "bible.html",
     "find": "    while (out.length > LOOKS_CAP){\n      var n = {};\n",
     "replace": "    return out.slice(-LOOKS_CAP);\n    while (out.length > LOOKS_CAP){\n      var n = {};\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2848 - the cells count fewer copies than his hand typed",
     "file": "bible.html",
     "find": "      if (_hcN > _nSg) _nSg = Math.min(_hcN, Math.max(_nSg, (have > 0) ? (have | 0) : 1));\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2848 - a sighting's mods never choose the copy",
     "file": "bible.html",
     "find": "      if (_mE.length === 1) hit = _mE[0];\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
