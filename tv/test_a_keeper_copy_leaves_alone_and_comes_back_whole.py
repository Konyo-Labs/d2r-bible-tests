# -*- coding: utf-8 -*-
"""#202 P3b (REG-2974, REG-2975) - A KEEPER'S COPIES STAY COPIES: A LOOK AT ONE NEVER DROPS ANOTHER, AND HIS HAND TAKES
OUT THE ONE IT NAMES AND CAN PUT IT BACK WHOLE.

Measured on the whole page in node, two Small Charms of Vita kept by the checker (+17 to Life, +20 to Life):
  * REG-2974 - one of them read at a stash cell: once a look named a cell the count was the cells (v3767), so the keeper
    counted 1 and the +20 copy's record was dropped on the next rebuild. A keeper's count only rises where a read or a pick
    plainly differs from every copy here (REG-2972, REG-2973), so each is a real item: the cells never count it below that;
  * REG-2975 - his hand removes copy 1 (the +17 one) through the trade door's copy-out (vaultRemoveCopy, REG-2849): the +20
    copy stayed, and its d2r_magicFinds record (the name's record, what copy 0 reads) still said +17. Copy 0 of a keeper
    reads its mods off that record, so the copy that leaves now carries them on its own row, the name's record takes the
    copy that is copy 0 now, and the journal's undo (vaultRestoreLast) puts the +17 copy back as copy 0, record and all;
  * the profile carries both copies' mods (d2r_vaultRecords and d2r_magicFinds ride in it).
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
           "localStorage.setItem('d2r_ownerClaim', '*'); localStorage.setItem('d2r_vaultAutoIntake', 'on');\n")
HELP = r"""
var W = window, N = 'Small Charm of Vita', T0 = Date.now();
function snap(){ try { W._vaultRecordsPersist(); } catch (e) {}
  return { n: copyCount(N), name: (magicFinds[N] || {}).mods || null,
           recs: (W._vaultRecords().records || []).filter(function(r){ return r.name === N; }).length,
           e: [0, 1].map(function(k){ var e = W._vaultCopyEntry(N, k); return e ? (e.mods || null) : null; }) }; }
"""
BODY = HELP + r"""
(function(){
function keep(mods, sid){ return W.aicJudgeApply({ ok: true, verdict: { tier: 'keep', score: 80 }, q: 'magic', base: 'Small Charm', name: N, mods: mods },
                                                  { sid: sid, frameId: sid + '_f', fts: Date.now() }); }
keep(['+17 to Life'], 's1'); keep(['+20 to Life'], 's2'); H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3);
OUT.kept = snap();
/* one copy read at a stash cell (a filed name's read joins its looks, REG-2848) */
var cell = { x: 4, y: 0, container: 'stash' }, at = new Date(T0 + 60000).toISOString();
OUT.reg = (W.tvVaultRegister(N, { by: 'tv-register', lane: 'stash', loc: 'stash', scene: 'stash', holder: 'MULE1', at: at, cell: cell,
  sessions: [{ session: 'h1', frame: 'h1_f', lane: 'stash', conf: 0.9, cell: cell, holder: 'MULE1', at: at },
             { session: 'h2', frame: 'h2_f', lane: 'stash', conf: 0.9, cell: cell, holder: 'MULE1', at: at }] }) || {}).mode || null;
H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3);
OUT.looked = { s: snap(), cells: (W._vaultSightGroups(N) || []).length };
/* his hand removes the +17 copy (copy 1, index 0) */
var r = W.vaultRemoveCopy(N, 0); H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3);
OUT.removed = { ok: !!(r && r.ok), s: snap() };
var b = W.vaultRestoreLast(); H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3);
OUT.restored = { r: b && b.restored, s: snap() };
OUT.text = W._vaultProfileBuild();
OUT.errors = H.errors.slice(0, 5);
})();
"""


def _load_body(text):
    return ("(function(){ var P = window._vaultProfileParse(" + json.dumps(text) + "); OUT.ok = !!(P && P.ok);"
            " Object.keys((P && P.stores) || {}).forEach(function(k){ var v = P.stores[k];"
            " if (v === null) window.LSR.removeItem(k); else window.LSR.setItem(k, v); });"
            " var d = {}; for (var i = 0; i < localStorage.length; i++){ var k = localStorage.key(i); d[k] = localStorage.getItem(k); } OUT.dump = d; })();")


AFTER = HELP + r"""
(function(){ try { W.renderVault(); } catch (e) {} H.flush(60, 3); OUT.loaded = snap(); OUT.errors = H.errors.slice(0, 5); })();
"""
L17, L20 = "+17 to Life", "+20 to Life"


class AKeeperCopyLeavesAloneAndComesBackWhole(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)
        ld = VPN.run(_load_body(cls.o["text"]), prelude=PRELUDE, timeout=300)
        cls.loaded_ok = ld.get("ok")
        seed = PRELUDE + "var __D = " + json.dumps(ld.get("dump") or {}) + "; Object.keys(__D).forEach(function(k){ localStorage.setItem(k, __D[k]); });\n"
        cls.a = VPN.run(AFTER, prelude=seed, timeout=300)

    def test_the_page_booted(self):
        for o in (self.o, self.a):
            self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
            self.assertEqual(o["errors"], [])
        self.assertTrue(self.loaded_ok, "PREMISE: the profile did not parse")
        self.assertEqual(self.o["kept"], {"n": 2, "name": [L17], "recs": 2, "e": [[L17], [L20]]}, "PREMISE: %r" % self.o["kept"])

    def test_a_look_at_one_copy_never_drops_the_other(self):
        lk = self.o["looked"]
        self.assertEqual((self.o["reg"], lk["cells"]), ("already", 1), "PREMISE: the read did not name one cell: %r" % lk)
        self.assertEqual(lk["s"], self.o["kept"], "one look at a cell dropped a copy: %r" % lk)

    def test_his_hand_takes_out_the_copy_it_names(self):
        rm = self.o["removed"]
        self.assertTrue(rm["ok"], rm)
        self.assertEqual(rm["s"], {"n": 1, "name": [L20], "recs": 1, "e": [[L20], None]},
                         "the +20 copy left, or the name's record still reads the copy that left: %r" % rm)

    def test_the_undo_puts_it_back_whole(self):
        rs = self.o["restored"]
        self.assertEqual(rs["r"], 1, rs)
        self.assertEqual(rs["s"], self.o["kept"], "the copy came back without its mods, or in the other's place: %r" % rs)

    def test_the_profile_carries_both_copies(self):
        self.assertEqual(self.a["loaded"], self.o["kept"], "the profile lost a keeper copy or its mods: %r" % self.a["loaded"])


RED_PROOF = [
    {"why": "REG-2974 - a look at one cell counts the keeper as the cells and drops the other copy",
     "file": "bible.html",
     "find": "      try { if (typeof magicFinds === 'object' && magicFinds && Object.prototype.hasOwnProperty.call(magicFinds, name) && (have | 0) > _nSg) _nSg = have | 0; } catch (eMfS) {}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2975 - the name's record keeps the mods of the copy that left",
     "file": "bible.html",
     "find": "        magicFinds[nm] = Object.assign({}, _mfK, { mods: _n0.entry.mods.slice(), base: _n0.entry.base || _mfK.base, q: _n0.entry.q || _mfK.q });\n",
     "replace": "        void 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2975 - copy 0 leaves without its mods, so its undo brings it back reading the other copy's",
     "file": "bible.html",
     "find": "    if (_mfK && k === 0 && !row.entry){ try { var _e0 = window._vaultCopyEntry(nm, 0); if (_e0) row.entry = _e0; } catch (eE0) {} }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2975 - copy 0 comes back and the name's record still reads the copy that stayed",
     "file": "bible.html",
     "find": "            magicFinds[_coN] = Object.assign({}, magicFinds[_coN], { mods: _coRow.entry.mods.slice(), base: _coRow.entry.base || magicFinds[_coN].base });\n",
     "replace": "            void 0;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
