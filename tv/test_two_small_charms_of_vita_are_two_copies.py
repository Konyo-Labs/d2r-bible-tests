# -*- coding: utf-8 -*-
"""#202 P3b (REG-2972) - TWO SMALL CHARMS OF VITA ARE TWO COPIES: A KEEPER'S READ IS JOINED TO ITS COPY BY ITS MODS.

A keeper is kept by NAME (d2r_magicFinds), so the AI checker's keep wrote each read over the last one. Measured on the whole
page in node: a Small Charm of Vita read +17 to Life, then another read +20 to Life -> one copy reading +20, the +17 charm
gone, and no copy records. The photo intake filled the first record and dropped the second the same way. Now both doors go
through ONE door, window._vaultKeeperReadJoin:
  * the same mods as a copy here is that copy (a re-read) - and a read that missed a line of it is still that copy;
  * mods that differ from every copy here (a line both carry with other numbers, or a line each has that the other lacks)
    are another copy: counted, and recorded with its own mods on its own record (copy 0 is the name's record);
  * a read with no mods tells nothing apart, so it is never a guessed copy;
  * a re-read of the same photo never counts another copy (REG-2401).
Driven on the whole page in node. RED_PROOF below.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
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
var W = window, N = 'Small Charm of Vita';
function keep(mods, sid){ var r = W.aicJudgeApply({ ok: true, verdict: { tier: 'keep', score: 80 }, q: 'magic', base: 'Small Charm', name: N, mods: mods },
                                                  { sid: sid, frameId: sid + '_f', fts: Date.now() });
  H.flush(60, 3); try { W.renderVault(); } catch (e) {} H.flush(60, 3); return r ? { mode: r.mode, copy: r.copy == null ? null : r.copy, newCopy: !!r.newCopy } : null; }
function snap(){ try { W._vaultRecordsPersist(); } catch (e) {}
  return { n: copyCount(N), name: (magicFinds[N] || {}).mods || null,
           recs: (W._vaultRecords().records || []).filter(function(r){ return r.name === N; }).length,
           e: [0, 1, 2].map(function(k){ var e = W._vaultCopyEntry(N, k); return e ? (e.mods || null) : null; }) }; }
OUT.a = { r: keep(['+17 to Life'], 's1'), s: snap() };
OUT.b = { r: keep(['+20 to Life'], 's2'), s: snap() };
OUT.c = { r: keep(['+17 to Life'], 's3'), s: snap() };
OUT.d = { r: keep(['+20 to Life', 'Required Level: 14'], 's4'), s: snap() };
OUT.e = { r: keep([], 's5'), s: snap() };
OUT.f = { r: keep(['+17 to Life', 'Required Level: 14'], 's6'), s: snap() };
OUT.g = { r: keep(['+17 to Life'], 's7'), s: snap() };
var S = W._vaultKeeperSameItem;
OUT.same = [
  S({ mods: ['+17 to Life'] }, { mods: ['+17 to life'] }),
  S({ mods: ['+17 to Life'] }, { mods: ['+20 to Life'] }),
  S({ mods: ['+17 to Life', '+5 to Strength'] }, { mods: ['+17 to Life'] }),
  S({ mods: ['+17 to Life', '+5 to Strength'] }, { mods: ['+17 to Life', '+9% Faster Hit Recovery'] }),
  S({ base: 'Small Charm', mods: ['+17 to Life'] }, { base: 'Grand Charm', mods: ['+17 to Life'] }),
  S({ base: 'cm1', mods: ['+17 to Life'] }, { base: 'Small Charm', mods: ['+17 to Life'] })];
OUT.errors = H.errors.slice(0, 5);
})();
"""


def _src():
    with open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


class TwoSmallCharmsOfVitaAreTwoCopies(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])
        self.assertEqual(self.o["a"]["s"], {"n": 1, "name": ["+17 to Life"], "recs": 1, "e": [["+17 to Life"], None, None]},
                         "PREMISE: the first keep: %r" % self.o["a"])

    def test_a_charm_with_other_mods_is_another_copy_with_its_own(self):
        b = self.o["b"]
        self.assertEqual((b["r"]["copy"], b["r"]["newCopy"]), (1, True), b)
        self.assertEqual(b["s"], {"n": 2, "name": ["+17 to Life"], "recs": 2, "e": [["+17 to Life"], ["+20 to Life"], None]},
                         "the second read wrote over the first, or kept its mods nowhere: %r" % b)

    def test_the_same_mods_again_are_that_copy(self):
        c = self.o["c"]
        self.assertEqual((c["r"]["copy"], c["r"]["newCopy"], c["s"]["n"]), (0, False, 2), c)

    def test_a_read_that_missed_or_added_a_line_is_still_that_copy(self):
        d = self.o["d"]
        self.assertEqual((d["r"]["copy"], d["r"]["newCopy"], d["s"]["n"]), (1, False, 2), d)
        self.assertEqual(d["s"]["e"][1], ["+20 to Life"], "a re-read wrote over the copy's mods: %r" % d)

    def test_a_re_read_of_copy_0_that_missed_a_line_keeps_its_lines(self):
        f, g = self.o["f"], self.o["g"]
        self.assertEqual((f["r"]["copy"], f["s"]["n"], f["s"]["name"]), (0, 2, ["+17 to Life", "Required Level: 14"]), f)
        self.assertEqual((g["r"]["copy"], g["s"]["n"]), (0, 2), g)
        self.assertEqual(g["s"]["name"], ["+17 to Life", "Required Level: 14"], "a re-read that missed a line wrote copy 0 shorter: %r" % g)

    def test_a_read_with_no_mods_is_never_a_guessed_copy(self):
        e = self.o["e"]
        self.assertEqual((e["r"]["newCopy"], e["s"]["n"]), (False, 2), e)

    def test_the_same_item_rule(self):
        self.assertEqual(self.o["same"], [True, False, True, False, False, True], self.o["same"])

    def test_the_photo_intake_goes_through_the_same_door(self):
        s = _src()
        call = ("window._vaultKeeperReadJoin(nm, { q: f.q || 'magic', base: f.base || '', mods: _mods }, "
                "{ sameFile: _intakeSameItem(fRec.prev, nm) })")
        self.assertEqual(s.count(call), 1, "the photo intake no longer asks the keeper door which copy a read is")
        at = s.index(call)
        self.assertEqual(len(re.findall(r"window\._vaultKeeperReadJoin\(", s)), 2, "a door counts keeper copies on its own")
        self.assertLess(s.index("(data.finds || []).forEach(function(f){"), at)


RED_PROOF = [
    {"why": "REG-2972 - a keeper's read with other mods is never counted as another copy",
     "file": "bible.html",
     "find": "    if (r.mode === 'new') copies[nm] = r.copyIx + 1;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2972 - another copy keeps its mods nowhere",
     "file": "bible.html",
     "find": "    if (r.copyIx > 0){ try { _vaultCopyEntrySet(nm, r.copyIx, entry, { fill: r.mode !== 'new' }); } catch (eKj) {} }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2972 - a read that missed a line is counted as another copy",
     "file": "bible.html",
     "find": "    return ka.every(function(t){ return B[t] != null; }) || kb.every(function(t){ return A[t] != null; });\n",
     "replace": "    return ka.length === kb.length && ka.every(function(t){ return B[t] != null; });\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2972 - the checker's keep writes every read over copy 0",
     "file": "bible.html",
     "find": "            var _kcR = (magicFinds[nm] && typeof magicFinds[nm] === 'object' && typeof window._vaultKeeperReadJoin === 'function')\n",
     "replace": "            var _kcR = (false && typeof window._vaultKeeperReadJoin === 'function')\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2972 - a re-read of copy 0 that missed a line writes it shorter",
     "file": "bible.html",
     "find": "              mods = magicFinds[nm].mods.slice();\n",
     "replace": "              void 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2972 - the photo intake counts no keeper copy",
     "file": "bible.html",
     "find": "              ? window._vaultKeeperReadJoin(nm, { q: f.q || 'magic', base: f.base || '', mods: _mods }, { sameFile: _intakeSameItem(fRec.prev, nm) }) : null;\n",
     "replace": "              ? null : null;\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
