# -*- coding: utf-8 -*-
"""REG-3054, REG-3055 (GrokBot #230, 2026-10-29 04:30) - A TV STUB'S 'basic' NEVER OUTRANKS WHAT THE NAME IS.

TV DIABLO stamps {rarity: 'basic', base: <its own name>, cat: 'TV-vaulted'} on a name nothing knew when it registered it.
His boards hold such stubs for runewords and rares: the Mac's "Heart of the Oak", the ALT's "Call to Arms", "Raven Whorl"
and "Doom Eye" (the ALT's without the val:'tv' mark the writers stamp today). Measured on the whole page in node with those
stubs: every one read rarity 'basic' (white), because _artRarity read the stub before findRuneword and never asked the
rolled-name grammar; Heart of the Oak, Call to Arms and Doom Eye drew an approx 1x2 (the stub's own name read as a base kept
the runeword out of _runewordCells); a runeword's picture asked "which base?" as if it were rolled; and Doom Eye's
unmarked stub routed to UNI-WEAPONS, so FIND sent him there.
  * REG-3054 - the order of authority: a catalogue runeword, his evidence's rarity and the rolled-name grammar outrank a
    stub's 'basic' over its own name (REG-2903 already reads that base as no base); an unmarked stub is read as a TV stub;
    the chronicle-apply writer never stubs a runeword the prune's catalogue keeps (d2rCatalogueKnows: the v739 writer's
    v2208 rule). A runeword that catalogue lacks (Heart of the Oak) keeps its stub - it is what keeps the name across a
    reload - and reads as a runeword all the same;
  * REG-3055 - a runeword with a stub is sized by its bases (_runewordCells: Heart of the Oak 2x3); Call to Arms, Fury,
    Dream and Lawbringer have no single size across their bases and stay an approx 1x2 BY DESIGN - until his copies'
    own records (REG-2844, REG-3002; REG-3001 shows them) settle it: every copy recorded in one footprint is that size.
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

TV = "\U0001F4FA TV-vaulted"
NAMES = ["Heart of the Oak", "Call to Arms", "Raven Whorl", "Doom Eye", "Fury", "Dream", "Lawbringer", "Zorblax Thing"]
STUBS = {n: {"rarity": "basic", "base": n, "cat": TV, "val": "tv"} for n in NAMES}
STUBS["Doom Eye"] = {"rarity": "basic", "base": "Doom Eye", "cat": TV}     # the ALT's shape: no val
STUBS["Raven Whorl"] = {"rarity": "basic", "base": "Raven Whorl", "cat": TV}
BASE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
        "localStorage.setItem('d2r_ownerClaim', '*');\n")
PRELUDE = (BASE + "localStorage.setItem('d2r_tvExtraItems', %s);\n" % json.dumps(json.dumps(STUBS))
           + "localStorage.setItem('d2r_owned', %s);\n" % json.dumps(json.dumps(NAMES)))
BODY = r"""
(function(){
var W = window, N = %s;
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); } H.flush(60, 3);
OUT.rows = {};
N.forEach(function(n){
  var sg = null; try { sg = W.suggestMule(n); } catch (e) {}
  var w = null; try { w = W._vaultWhereIs(n); } catch (e) {}
  var c = _itemCells(n);
  OUT.rows[n] = { rar: W._artRarity(n), cells: [c.w, c.h, !!c.approx], ask: (W._artRolledBase(n) || {}).ask || null,
                  mule: sg ? sg.id : null, find: w ? w.mule || null : null };
});
OUT.errors = H.errors.slice(0, 5);
})();
""" % json.dumps(NAMES)
FOOT = r"""
(function(){
var W = window, N = 'Fury';
function judge(b, sid){ W.aicJudgeApply({ ok: true, verdict: { tier: 'keep', score: 90 }, q: 'runeword', base: b, name: N, mods: [] },
  { sid: sid, frameId: sid + '_f', fts: Date.now(), loc: 'stash', scene: 'stash' }); H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3);
  var c = _itemCells(N); return [c.w, c.h, !!c.approx]; }
var c0 = _itemCells(N); OUT.none = [c0.w, c0.h, !!c0.approx];
OUT.pb = judge('Phase Blade', 's1');
_mkSetWant(N, 3);
OUT.ba = judge('Berserker Axe', 's2');
OUT.cb = judge('Colossus Blade', 's3');
OUT.copies = copyCount(N);
OUT.errors = H.errors.slice(0, 5);
})();
"""
WRITER = r"""
(function(){
var W = window;
W._vaultAutoIntakeSet && W._vaultAutoIntakeSet(true);
/* REG-3086 - the apply reaches the vault only through its door, which owns a read on two sessions' looks: each row carries
   them (a row with no look was owned by toggleOwned's physical arm before, with no gate at all) */
var L2 = function(i){ return [{ session: 's_17900000000' + i + '1_00001', frame: 'f_17900000000' + i + '1.jpg', lane: 'stash', conf: 0.9 },
                              { session: 's_17900000000' + i + '2_00002', frame: 'f_17900000000' + i + '2.jpg', lane: 'stash', conf: 0.9 }]; };
W.chronicleApply({ wouldAdd: { uniques: [{ name: 'Enigma', loc: 'stash', witnesses: L2(1) }, { name: 'Heart of the Oak', loc: 'stash', witnesses: L2(2) },
                                         { name: 'Zorblax Spire', loc: 'stash', witnesses: L2(3) }], sets: [] } });
H.flush(60, 3);
var st = JSON.parse(W.LSR.getItem('d2r_tvExtraItems') || '{}');
OUT.knows = [!!W.d2rCatalogueKnows('Enigma'), !!W.d2rCatalogueKnows('Heart of the Oak')];
OUT.stubbed = { enigma: !!st['Enigma'], hoto: !!st['Heart of the Oak'], other: !!st['Zorblax Spire'], owned: owned.has('Enigma') && owned.has('Heart of the Oak') };
OUT.rar = W._artRarity('Heart of the Oak');
OUT.errors = H.errors.slice(0, 5);
})();
"""


class ATvStubNeverOutranksWhatTheNameIs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)
        cls.f = VPN.run(FOOT, prelude=PRELUDE, timeout=300)
        cls.w = VPN.run(WRITER, prelude=BASE, timeout=300)

    def r(self, n):
        return self.o["rows"][n]

    def test_the_page_booted(self):
        for o in (self.o, self.f, self.w):
            self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
            self.assertEqual(o["errors"], [])
        self.assertNotIn("renderErr", self.o, self.o.get("renderErr"))

    def test_a_runeword_with_a_stub_is_a_runeword(self):
        for n in ("Heart of the Oak", "Call to Arms", "Fury", "Dream", "Lawbringer"):
            self.assertEqual(self.r(n)["rar"], "rw", "%s read as %r from its TV stub" % (n, self.r(n)["rar"]))
            self.assertIsNone(self.r(n)["ask"], "%s's picture asks which base, as if it were rolled" % n)

    def test_a_rolled_rare_with_a_stub_is_what_its_grammar_says(self):
        for n in ("Raven Whorl", "Doom Eye"):
            self.assertEqual(self.r(n)["rar"], "rare", "%s read as %r" % (n, self.r(n)["rar"]))
            self.assertEqual(self.r(n)["cells"], [1, 1, False], "%s is not sized as its slot: %r" % (n, self.r(n)))
        self.assertTrue(self.r("Raven Whorl")["ask"], "PREMISE (REG-2903): a ring or a jewel is still asked")

    def test_a_stub_of_a_name_nothing_knows_keeps_its_word(self):
        self.assertEqual(self.r("Zorblax Thing")["rar"], "basic", self.r("Zorblax Thing"))

    def test_an_unmarked_stub_is_a_tv_stub_for_the_router_and_find(self):
        d = self.r("Doom Eye")
        self.assertEqual((d["mule"], d["find"]), ("magic-rare", "magic-rare"), "Doom Eye's unmarked stub routed by its word: %r" % d)

    def test_a_runeword_is_sized_by_its_bases_and_no_single_size_stays_approx(self):
        self.assertEqual(self.r("Heart of the Oak")["cells"], [2, 3, False], self.r("Heart of the Oak"))
        for n in ("Call to Arms", "Fury", "Dream", "Lawbringer"):
            self.assertEqual(self.r(n)["cells"], [1, 2, True], "%s: no single size across its bases is approx, by design: %r" % (n, self.r(n)))

    def test_his_copies_recorded_in_one_size_are_that_size(self):
        f = self.f
        self.assertEqual(f["none"], [1, 2, True], "PREMISE: %r" % f)
        self.assertEqual((f["pb"], f["ba"]), ([2, 3, False], [2, 3, False]), "the recorded bases never sized it: %r" % f)
        self.assertEqual((f["cb"], f["copies"]), ([1, 2, True], 3), "two footprints across his copies were given one: %r" % f)

    def test_the_chronicle_writer_stubs_only_what_the_prune_needs(self):
        s = self.w["stubbed"]
        self.assertTrue(s["owned"] and s["other"], "PREMISE: the apply did not reach the vault: %r" % s)
        self.assertEqual(self.w["knows"], [True, False], "PREMISE: the prune's catalogue (RUNEWORDS) changed: %r" % self.w["knows"])
        self.assertFalse(s["enigma"], "a runeword the prune's catalogue keeps was stubbed as basic: %r" % s)
        self.assertTrue(s["hoto"], "a runeword the prune's catalogue lacks lost the stub that keeps it across a reload: %r" % s)
        self.assertEqual(self.w["rar"], "rw", "its stub made it white again: %r" % self.w)


RED_PROOF = [
    {"why": "REG-3054 - a TV stub's 'basic' is read before the catalogue runeword",
     "file": "bible.html",
     "find": "    if (!r && !_blindBasic && typeof EXTRA_ITEMS !== 'undefined' && EXTRA_ITEMS[name]){\n",
     "replace": "    if (!r && typeof EXTRA_ITEMS !== 'undefined' && EXTRA_ITEMS[name]){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3054 - a blind stub's rare is never asked of the grammar",
     "file": "bible.html",
     "find": "      try { var _rqB = (typeof _rolledQuality === 'function') ? _rolledQuality(name) : null; if (_rqB && (_rqB.q === 'magic' || _rqB.q === 'rare')) r = _rqB.q; } catch (eRqB) {}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3054 - a stub stored without val:'tv' is read as a curated entry",
     "file": "bible.html",
     "find": "    if (_e.val == null && /TV-vaulted/.test(String(_e.cat || ''))) _e.val = 'tv';\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3054 - a runeword's stub makes its picture ask which base",
     "file": "bible.html",
     "find": "  if (ex && ex.val === 'tv' && String(ex.base || '') === nm && typeof findRuneword === 'function' && findRuneword(nm)) return out;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3054 - the chronicle-apply writer stubs a runeword the prune's catalogue keeps",
     "file": "bible.html",
     "find": "            if (typeof window._tvExtraRemember === 'function' && !(typeof window.d2rCatalogueKnows === 'function' && window.d2rCatalogueKnows(n))) {\n",
     "replace": "            if (typeof window._tvExtraRemember === 'function') {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3055 - a runeword's stub keeps it out of its bases' size",
     "file": "bible.html",
     "find": "      if (!base || (_stubOwn && typeof findRuneword === 'function' && findRuneword(name))){   /* REG-3055 a stub's own name is no base */\n",
     "replace": "      if (!base){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3055 - his copies' recorded bases never size a runeword",
     "file": "bible.html",
     "find": "        _storedBase = String(window._vaultCopyBaseCode(name) || '');\n",
     "replace": "        void 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3055 - two footprints across his copies are given one size",
     "file": "bible.html",
     "find": "          if (!m.size){ m.size = sz; m.code = b; } else if (m.size !== sz) m.ok = false;\n",
     "replace": "          if (!m.size){ m.size = sz; m.code = b; }\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
