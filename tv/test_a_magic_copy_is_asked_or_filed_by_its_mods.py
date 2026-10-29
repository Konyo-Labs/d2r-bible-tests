# -*- coding: utf-8 -*-
"""#202 P3b (REG-2973) - A KEEPER PICKED AGAIN IN THE PLANNER IS ASKED OR FILED BY ITS MODS, AND ANOTHER COPY IS COUNTED.

A Magic & Rare keeper is homed by the keeper rule, never in the mule map, so the planner's copy count never reached it.
Measured on the whole page in node: Small Charm of Vita +17 and then +20 from the planner -> one copy reading +17, the +20
charm gone. And the join question compared affix ids on the pick with read lines on each copy, so the two always differed:
the same +17 typed again was "another copy" too, and dropped the same way. Now:
  * a pick's affix lines are its mods (_vpMods), on its record and in the question;
  * mods that differ from every copy here file another copy, counted, carrying its own entry;
  * the same lines (or a copy that shows more lines of the same item) are asked - the same item, or another copy;
  * "the same item" completes THAT copy, never writes over what a read gave it; a copy 0 read with no mods takes his
    lines, on its record and on the name's record;
  * "another copy" never gives its mods to copy 0, and neither does "the same as copy 2";
  * a read of the checker after the pick joins the copy the pick made (one door: _vaultKeeperSameItem).
Driven on the whole page in node. RED_PROOF below.
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
HELP = r"""
var W = window, DB = W._cbDb(), N = 'Small Charm of Vita';
function code(n){ return Object.keys(DB.b).find(function(c){ return DB.b[c][0] === n; }); }
function cur(){ var s = W._cbState(); return s && s.host && s.host.cur ? s.host.cur() : null; }
function keep(mods, sid){ var r = W.aicJudgeApply({ ok: true, verdict: { tier: 'keep', score: 80 }, q: 'magic', base: 'Small Charm', name: N, mods: mods },
                                                  { sid: sid, frameId: sid + '_f', fts: Date.now() });
  H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3); return r ? { copy: r.copy == null ? null : r.copy, newCopy: !!r.newCopy } : null; }
/* a magic Small Charm, of Vita at the roll given; Done; then his answer when it asks */
function pick(v, answer){
  W.vaultPlannerOpen(''); W._cbChoose('b:' + code('Small Charm')); W._cbQuality('m'); H.flush(60, 3);
  var P = W._cbAffixPool(cur()).rows, vita = (P.s || []).filter(function(r){ var a = W._cbAf(r[0]); return a && /^of vita$/i.test(String(a[2])); })[0];
  W._cbAddMod(vita[0]); cur().affixes[0].rolls = { m1: v };
  var done = W.vaultPlannerClose(); H.flush(60, 3);
  var q = W._cbState() && W._cbState().host && W._cbState().host.question;
  var asked = q ? (q.choices || []).length : 0;
  if (q && answer != null){ W.vaultPlannerAnswer(answer); H.flush(60, 3); W.vaultPlannerClose(); H.flush(60, 3); }
  return { done: done, asked: asked };
}
function snap(){ try { W._vaultRecordsPersist(); } catch (e) {}
  return { n: copyCount(N), name: (magicFinds[N] || {}).mods || null,
           e: [0, 1, 2].map(function(k){ var e = W._vaultCopyEntry(N, k); return e ? (e.mods || null) : null; }) }; }
function ax(k){ var e = W._vaultCopyEntry(N, k); return ((e && e.affixes) || []).map(function(a){ return a.id; }); }
"""
BODY = HELP + r"""
(function(){
OUT.a = { r: keep(['+17 to Life', 'Required Level: 14'], 's1'), s: snap() };
OUT.b = { p: pick(20, null), s: snap() };
OUT.c = { p: pick(17, 0), s: snap() };
OUT.d = { r: keep(['+20 to Life'], 's2'), s: snap() };
OUT.errors = H.errors.slice(0, 5);
})();
"""
BARE_COPY = HELP + r"""
(function(){
OUT.a = { r: keep([], 's1'), s: snap() };
OUT.b = { p: pick(17, 'copy'), s: snap() };
OUT.errors = H.errors.slice(0, 5);
})();
"""
BARE_SAME = HELP + r"""
(function(){
OUT.a = { r: keep([], 's1'), s: snap() };
OUT.b = { p: pick(17, 0), s: snap() };
OUT.errors = H.errors.slice(0, 5);
})();
"""
NEW_PICK = HELP + r"""
(function(){ OUT.a = { p: pick(17, null), s: snap(), ax0: ax(0) }; OUT.errors = H.errors.slice(0, 5); })();
"""
READ_SAME_1 = HELP + r"""
(function(){
keep(['+17 to Life'], 's1'); keep(['+20 to Life'], 's2');
OUT.a = { s: snap(), ax1: ax(1) };
OUT.b = { p: pick(20, 1), s: snap(), ax1: ax(1) };
OUT.errors = H.errors.slice(0, 5);
})();
"""
BARE_SAME_1 = HELP + r"""
(function(){
keep([], 's1'); pick(20, 'copy');
OUT.a = { s: snap() };
OUT.b = { p: pick(20, 1), s: snap() };
OUT.errors = H.errors.slice(0, 5);
})();
"""
L17, L20, REQ = "+17 to Life", "+20 to Life", "Required Level: 14"


class AMagicCopyIsAskedOrFiledByItsMods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)
        cls.bc = VPN.run(BARE_COPY, prelude=PRELUDE, timeout=300)
        cls.bs = VPN.run(BARE_SAME, prelude=PRELUDE, timeout=300)
        cls.np = VPN.run(NEW_PICK, prelude=PRELUDE, timeout=300)
        cls.r1 = VPN.run(READ_SAME_1, prelude=PRELUDE, timeout=300)
        cls.b1 = VPN.run(BARE_SAME_1, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        for o in (self.o, self.bc, self.bs, self.np, self.r1, self.b1):
            self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
            self.assertEqual(o["errors"], [])
        self.assertEqual(self.o["a"]["s"], {"n": 1, "name": [L17, REQ], "e": [[L17, REQ], None, None]}, "PREMISE: %r" % self.o["a"])

    def test_a_pick_with_other_mods_files_another_copy_with_its_own(self):
        b = self.o["b"]
        self.assertEqual(b["p"]["asked"], 0, "a +20 charm beside a +17 one was asked: %r" % b)
        self.assertEqual(b["s"], {"n": 2, "name": [L17, REQ], "e": [[L17, REQ], [L20], None]},
                         "the planner's second charm was dropped, or kept its mods nowhere: %r" % b)

    def test_the_same_lines_are_asked_and_the_same_item_keeps_what_was_read(self):
        c = self.o["c"]
        self.assertEqual(c["p"]["asked"], 2, "the same +17 was not asked: %r" % c)
        self.assertEqual(c["s"], {"n": 2, "name": [L17, REQ], "e": [[L17, REQ], [L20], None]},
                         "his 'same item' added a copy or wrote over what the read gave copy 0: %r" % c)

    def test_a_read_after_the_pick_joins_the_copy_the_pick_made(self):
        d = self.o["d"]
        self.assertEqual((d["r"]["copy"], d["r"]["newCopy"], d["s"]["n"]), (1, False, 2), d)

    def test_another_copy_never_gives_its_mods_to_copy_0(self):
        b = self.bc["b"]
        self.assertEqual(b["p"]["asked"], 1, "PREMISE: a keeper read with no mods is asked: %r" % b)
        self.assertEqual(b["s"], {"n": 2, "name": [], "e": [None, [L17], None]}, "copy 0 took the new copy's mods: %r" % b)

    def test_the_same_item_gives_copy_0_his_lines(self):
        b = self.bs["b"]
        self.assertEqual(b["s"], {"n": 1, "name": [L17], "e": [[L17], None, None]}, "his lines never reached copy 0: %r" % b)

    def test_a_new_keeper_from_the_planner_carries_its_pick(self):
        a = self.np["a"]
        self.assertEqual(a["s"], {"n": 1, "name": [L17], "e": [[L17], None, None]}, a)
        self.assertEqual(a["ax0"], ["s349"], "the planner's keeper keeps its pick (the affix he chose) nowhere: %r" % a)

    def test_the_same_as_a_read_copy_completes_that_copy(self):
        a, b = self.r1["a"], self.r1["b"]
        self.assertEqual((a["s"]["n"], a["ax1"]), (2, []), "PREMISE: two read copies, none picked: %r" % a)
        self.assertEqual(b["p"]["asked"], 2, b)
        self.assertEqual(b["s"], {"n": 2, "name": [L17], "e": [[L17], [L20], None]}, b)
        self.assertEqual(b["ax1"], ["s349"], "his 'same as copy 2' reached no copy: %r" % b)

    def test_the_same_as_copy_2_never_gives_its_mods_to_copy_0(self):
        a, b = self.b1["a"], self.b1["b"]
        self.assertEqual(a["s"], {"n": 2, "name": [], "e": [None, [L20], None]}, "PREMISE: %r" % a)
        self.assertEqual(b["p"]["asked"], 2, b)
        self.assertEqual(b["s"], a["s"], "his 'same as copy 2' wrote copy 2's mods on copy 0: %r" % b)


RED_PROOF = [
    {"why": "REG-2973 - a keeper picked again is never counted as another copy",
     "file": "bible.html",
     "find": "      else if (routed.mode === 'already' && _mfAnother && assign[nm] == null && typeof copies !== 'undefined' && copies){\n",
     "replace": "      else if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - the question compares affix ids with read lines, so the same +17 is filed as another copy",
     "file": "bible.html",
     "find": "    if (/^(m|magic|rare|c|crafted)$/.test(_jqQ) && typeof window._vaultKeeperSameItem === 'function'){\n",
     "replace": "    if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - a pick's record carries no mod lines",
     "file": "bible.html",
     "find": "    if (!out.mods && /^(m|magic|rare|c|crafted)$/.test(out.q || '') && out.affixes.length && typeof window._vpMods === 'function'){\n",
     "replace": "    if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - a magic pick's copy records no entry",
     "file": "bible.html",
     "find": "    if (kept && _vpMade.copyIx != null && typeof window._vaultCopyEntrySet === 'function'){\n",
     "replace": "    if (!magicQ && kept && _vpMade.copyIx != null && typeof window._vaultCopyEntrySet === 'function'){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - another copy gives its mods to copy 0",
     "file": "bible.html",
     "find": "mods && mods.length && !_mfAnother) _mfHad.mods = mods;\n",
     "replace": "mods && mods.length) _mfHad.mods = mods;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - 'the same item' writes nothing on a keeper copy",
     "file": "bible.html",
     "find": "    if (mark.entry && typeof window._vaultCopyEntrySet === 'function'){\n",
     "replace": "    if (mark.entry && !/^(m|magic|rare|c|crafted)$/.test(String(mark.entry.q || '')) && typeof window._vaultCopyEntrySet === 'function'){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - 'the same as copy 2' gives its mods to copy 0's name record",
     "file": "bible.html",
     "find": "    if (magicQ && !((copyIx | 0) > 0) && typeof magicFinds !== 'undefined' && magicFinds && magicFinds[nm] && typeof magicFinds[nm] === 'object'){\n",
     "replace": "    if (magicQ && typeof magicFinds !== 'undefined' && magicFinds && magicFinds[nm] && typeof magicFinds[nm] === 'object'){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2973 - 'the same item' writes over the lines a read gave copy 0",
     "file": "bible.html",
     "find": "    if (!row.entry && opts.fill && k === 0 && typeof magicFinds === 'object' && magicFinds && magicFinds[nm] && typeof magicFinds[nm] === 'object'){\n",
     "replace": "    if (false){\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
