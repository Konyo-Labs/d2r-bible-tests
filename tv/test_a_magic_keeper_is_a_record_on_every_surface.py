# -*- coding: utf-8 -*-
"""#202 P3b (REG-2971) - EVERY MAGIC & RARE KEEPER IS A RECORD, HOMED BY THE KEEPER RULE, AND DRAWN ONCE PER COPY.

A keeper (d2r_magicFinds) is a rolled name no catalogue holds, so ownedPool left it out and no copy of it had a record: no
entry, no copy count, no MOVE row, nothing the per-copy doors (REG-2844 entries, REG-2849 removal) could hold. Measured on
the whole page in node: a kept Small Charm of Vita, owned and homed on the shared stash, had 0 records, and the shared stash
window drew no tile of it. Now:
  * every keeper is in the records pool, one record per copy;
  * its record takes the home the keeper rule gives it (_mfKeeperHome, REG-2895) - a charm on the SHARED STASH, any other
    keeper on MAGIC & RARE (REG-2853);
  * a keeper homed on the shared stash is drawn as its keeper cells only. Once it had records there it came in twice: two
    Small Charms of Vita drew 3 cells on the shared stash card and the card said "1 item in 3 copies";
  * a keeper held twice draws two keeper cells (REG-2973), each titled with that copy's own mods, and the card says
    "1 item in 2 copies", as the locker window counts. A cell held more than once takes out THAT copy (vaultRemoveCopy);
    the last copy's X throws the keeper out of Magic & Rare as before.
Driven on the whole page in node. RED_PROOF below.
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
var W = window, C = 'Small Charm of Vita', R = 'Rune Loop', J = 'Doom Band';
function keep(n, q, base, mods, sid){ return W.aicJudgeApply({ ok: true, verdict: { tier: 'keep', score: 80 }, q: q, base: base, name: n, mods: mods },
                                                             { sid: sid, frameId: sid + '_f', fts: Date.now() }); }
keep(C, 'magic', 'Small Charm', ['+17 to Life'], 's1'); keep(C, 'magic', 'Small Charm', ['+20 to Life'], 's2');
keep(R, 'rare', 'Ring', ['+1 to All Skills', '10% Faster Cast Rate'], 's3'); keep(R, 'rare', 'Ring', ['5% Life stolen per hit', '+30 to Mana'], 's4');
keep(J, 'rare', 'Ring', ['+2 to Mana after each Kill'], 's5');
H.flush(60, 3); try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); } H.flush(60, 3);
var shelf = String((document.getElementById('vault-shelf') || {}).innerHTML || '');
function card(id){ var at = shelf.indexOf('data-vault-mule="' + id + '"'), nx = at < 0 ? -1 : shelf.indexOf('data-vault-mule="', at + 10); return at < 0 ? '' : shelf.slice(at, nx < 0 ? shelf.length : nx); }
function un(s){ return String(s).replace(/&#39;/g, "'").replace(/&amp;/g, '&').replace(/&quot;/g, '"'); }
function cells(s, n){ var o = []; s.replace(/<div class="vm-cell vmc-magicfind[^>]*>[\s\S]*?<\/button><\/div>/g, function(c){
    if (c.indexOf('data-magic-find="' + n + '"') < 0) return c;
    var t = /title="([^"]*)"/.exec(c), xs = c.match(/<button class="vm-unassign vm-cell-x" onclick="[^"]*"/g) || [];
    var x = xs.length ? /onclick="([^"]*)"/.exec(xs[xs.length - 1]) : null;
    o.push({ title: t ? un(t[1]) : null, x: x ? un(x[1]) : null }); return c; }); return o; }
function recCells(s, n){ return s.split('data-vault-item="' + n + '"').length - 1; }
var cs = card('shared'), cm = card('magic-rare');
OUT.homes = [W._mfKeeperHome(C), W._mfKeeperHome(R), W._mfKeeperHome(J)];
OUT.copies = [copyCount(C), copyCount(R), copyCount(J)];
OUT.recs = (W._vaultRecords().records || []).filter(function(r){ return r.name === C || r.name === R || r.name === J; })
  .map(function(r){ return [r.name, r.copyIx, r.kind, r.mule || null]; });
OUT.shared = { C: cells(cs, C), recC: recCells(cs, C), copies: (/class="vm-copies"[^>]*>([^<]*)/.exec(cs) || [])[1] || null };
OUT.mr = { R: cells(cm, R), J: cells(cm, J), copies: (/class="vm-copies"[^>]*>([^<]*)/.exec(cm) || [])[1] || null };
['magic-rare', 'shared'].forEach(function(id){
  try { W.openMuleCard(id); } catch (e) { OUT['openErr_' + id] = String(e && e.message || e); }
  H.flush(60, 3);
  var det = String((document.getElementById('vault-detail') || {}).innerHTML || '');
  var txt = det.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  OUT['win_' + id] = { C: det.indexOf(C) >= 0, calc: (/Items in this locker (\d+) Copies \(physical\) (\d+)/.exec(txt) || []).slice(1).map(Number) };
});
OUT.errors = H.errors.slice(0, 5);
})();
"""


class AMagicKeeperIsARecordOnEverySurface(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertNotIn("renderErr", self.o, self.o.get("renderErr"))
        self.assertEqual(self.o["errors"], [])
        self.assertEqual(self.o["homes"], ["shared", "magic-rare", "magic-rare"], "PREMISE: the keeper rule homes: %r" % self.o["homes"])
        self.assertEqual(self.o["copies"], [2, 2, 1], "PREMISE: the reads were not counted as copies: %r" % self.o["copies"])

    def test_each_copy_of_each_keeper_is_a_record_at_its_keeper_home(self):
        self.assertEqual(sorted(map(tuple, self.o["recs"])), [
            ("Doom Band", 0, "filed", "magic-rare"),
            ("Rune Loop", 0, "filed", "magic-rare"), ("Rune Loop", 1, "filed", "magic-rare"),
            ("Small Charm of Vita", 0, "sharedStash", None), ("Small Charm of Vita", 1, "sharedStash", None)], self.o["recs"])

    def test_the_shared_stash_card_draws_the_charm_once_per_copy(self):
        s = self.o["shared"]
        self.assertEqual(s["recC"], 0, "the charm came in twice - as keeper cells and as record cells: %r" % s)
        self.assertEqual(len(s["C"]), 2, s)
        self.assertEqual(s["copies"], "1 item in 2 copies", s)

    def test_each_copy_cell_says_its_own_mods_and_takes_out_that_copy(self):
        c = self.o["shared"]["C"]
        self.assertIn("copy 1 of 2", c[0]["title"]); self.assertIn("+17 to Life", c[0]["title"])
        self.assertIn("copy 2 of 2", c[1]["title"]); self.assertIn("+20 to Life", c[1]["title"])
        self.assertIn("vaultRemoveCopy('Small Charm of Vita', 0)", c[0]["x"], c)
        self.assertIn("vaultRemoveCopy('Small Charm of Vita', 1)", c[1]["x"], c)

    def test_magic_and_rare_draws_as_many_cells_as_its_window_counts(self):
        m, w = self.o["mr"], self.o["win_magic-rare"]
        self.assertEqual((len(m["R"]), len(m["J"])), (2, 1), m)
        self.assertEqual(w["calc"], [2, 3], "the window's count: %r" % w)
        self.assertEqual(m["copies"], "2 items in 3 copies", m)

    def test_a_keeper_held_once_keeps_its_throw_out(self):
        j = self.o["mr"]["J"][0]
        self.assertIn("vaultThrowFind('Doom Band')", j["x"], j)
        self.assertNotIn("copy 1 of", j["title"], j)

    def test_the_shared_stash_window_draws_the_charm(self):
        self.assertTrue(self.o["win_shared"]["C"], "the shared stash window drew no tile of the kept charm: %r" % self.o["win_shared"])


RED_PROOF = [
    {"why": "REG-2971 - the keepers stay out of the records pool: 0 records",
     "file": "bible.html",
     "find": "      try { if (typeof magicFinds === 'object' && magicFinds) Object.keys(magicFinds).forEach(function(n){ if (n && poolAll.indexOf(n) < 0) poolAll.push(n); }); } catch (eMfP) {}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2971 - a charm's record is homed on MAGIC & RARE, not where the keeper rule (and the card) puts it",
     "file": "bible.html",
     "find": "        else if (typeof window._mfKeeperHome === 'function' && window._mfKeeperHome(name) === 'shared') kind = 'sharedStash';\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2971 - a keeper on the shared stash is drawn as keeper cells AND record cells",
     "file": "bible.html",
     "find": "        items = items.filter(function(n){ return !(Object.prototype.hasOwnProperty.call(magicFinds, n) && _mfKeeperHome(n) === m.id); });\n",
     "replace": "        void 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - a keeper held twice is drawn once",
     "file": "bible.html",
     "find": "          var _mfN = (typeof copyCount === 'function') ? Math.max(1, copyCount(n) | 0) : 1, _mfCells = [];\n",
     "replace": "          var _mfN = 1, _mfCells = [];\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - the card's copies line leaves the keepers' extra copies out",
     "file": "bible.html",
     "find": "      var _copyN = total + _ovCopyN + _mfCopyX;\n",
     "replace": "      var _copyN = total + _ovCopyN;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
