# -*- coding: utf-8 -*-
"""REG-3004 (his Q5, 2026-10-29) - A RUNE, GEM, MATERIAL OR REJUVENATION POTION TYPED BY HAND MOVES ITS TALLY, UP OR DOWN,
THROUGH THE TOOLS TAB'S OWN DOOR - ONE DOOR, NO SECOND COUNTER.

His ask: a rune/gem/material hand add may move its tally up or down, and the tools section already has a tally up/down
control for a misread. It does: the Rune Stash, Gem Stash and Materials cards on the Tools tab move a count one at a time
(click +1, right-click or the minus button -1) through adjustRuneStash / adjustGemStash / adjustMaterialStash, and the
read funnel (tvToolsDelta) moves them through the same three. The hand door refused instead (REG-2857 / REG-2899:
"counted in the Rune Stash ... nothing was added"), and the TV read chip's +1 wrote the stores itself - a second
counter beside the door. Now:
  * vaultHandAdd(count, at, {delta}) moves that count's tally by delta (+1 when not said) through its own adjust function,
    chosen by _stashTallyOf (REG-2899's one rule), and owns nothing; -1 takes one off and never goes below zero;
  * + Add an item lists a count as its tally's row with -1 / +1, and Enter on it is its +1;
  * the read chip's +1 asks the same door.
Driven on the whole page in node (vault_page_node), a spy on each door, fixtures only. RED_PROOF below.
"""
import os
import re
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

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
SEED = "localStorage.setItem('d2r_ownerClaim', '*');\n"
BODY = r"""
(function(){
var W = window;
var calls = [];
['adjustRuneStash', 'adjustGemStash', 'adjustMaterialStash'].forEach(function(f){
  var real = W[f];
  W[f] = function(n, d){ calls.push([f, n, d]); return real.apply(this, arguments); };
});
function counts(){ return { ber: (W.runeStash || {})['Ber'] || 0, ame: (W.gemStash || {})['Perfect Amethyst'] || 0,
                            key: (W.materialStash || {})['Key of Terror'] || 0 }; }
var owned0 = Array.from(owned).length;
OUT.before = counts();
OUT.up = ['Ber', 'Perfect Amethyst', 'Key of Terror'].map(function(n){ var a = W.vaultHandAdd(n, null, {});
  return a && { ok: a.ok, mode: a.mode, kind: a.kind, was: a.was, now: a.now, why: a.why }; });
OUT.afterUp = counts();
OUT.down = W.vaultHandAdd('Ber Rune', null, { delta: -1 });
OUT.afterDown = counts();
OUT.under = W.vaultHandAdd('Ber', null, { delta: -1 });
OUT.afterUnder = counts();
OUT.callsHand = calls.slice();
OUT.ownedMoved = Array.from(owned).length - owned0;
/* + Add an item: a typed count is its tally's row; its +1 and Enter move it through the same door */
calls.length = 0;
W.vaultHandOpen(); var qi = document.getElementById('vault-hand-q'); if (qi) qi.value = 'Ber'; var s = W.vaultHandSearch('Ber');
var list = String((document.getElementById('vault-hand-list') || {}).innerHTML || '');
OUT.row = { tallies: (s && s.tallies || []).map(function(t){ return t.name + '|' + t.count; }),
            hasRow: /data-state="tally" data-tally="Ber Rune"/.test(list), minus: /vaultHandTally\(.{0,80}?, -1\)">\u22121</.test(list),
            plus: /vaultHandTally\(.{0,80}?, 1\)">\+1</.test(list) };
OUT.take = W.vaultHandTally('Ber Rune', 1);
OUT.enter = W._vaultHandKey({ key: 'Enter', preventDefault: function(){} });
OUT.afterBox = counts();
OUT.callsBox = calls.slice();
W.vaultHandClose();
/* the read chip's +1 */
calls.length = 0;
W._tvdApply({ closest: function(){ return null; } }, 'gem', 'Perfect Amethyst');
OUT.callsChip = calls.slice();
OUT.afterChip = counts();
OUT.ownedAfter = Array.from(owned).length - owned0;
})();
"""


def _code():
    with open(PAGE, encoding="utf-8") as fh:
        src = fh.read()
    src = re.sub(r"/\*.{0,4000}?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(^|[^:\\'\"])//[^\n]*", r"\1", src)


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AHandAddMovesACountThroughTheToolsDoor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=SEED, timeout=300)

    def test_a_hand_add_moves_the_tally_up_through_its_own_door(self):
        o = self.o
        self.assertEqual(o["before"], {"ber": 0, "ame": 0, "key": 0}, "premise: a fixture with empty tallies")
        for a, kind in zip(o["up"], ("rune", "gem", "material")):
            self.assertTrue(a and a["ok"] and a["mode"] == "tallied", "a hand add of a %s did not move its tally: %r" % (kind, a))
            self.assertEqual((a["kind"], a["was"], a["now"]), (kind, 0, 1), a)
        self.assertEqual(o["afterUp"], {"ber": 1, "ame": 1, "key": 1})
        self.assertIn(["adjustRuneStash", "Ber", 1], o["callsHand"], "the hand's +1 did not go through the Rune Stash's door")
        self.assertIn(["adjustGemStash", "Perfect Amethyst", 1], o["callsHand"])
        self.assertIn(["adjustMaterialStash", "Key of Terror", 1], o["callsHand"])
        self.assertEqual(o["ownedMoved"], 0, "a count reached his owned list")

    def test_a_hand_add_moves_it_down_and_never_below_zero(self):
        o = self.o
        self.assertTrue(o["down"]["ok"] and o["down"]["mode"] == "tallied", o["down"])
        self.assertEqual(o["afterDown"]["ber"], 0, "-1 did not take one off")
        self.assertIn(["adjustRuneStash", "Ber", -1], o["callsHand"], "the hand's -1 did not go through the door")
        self.assertFalse(o["under"]["ok"], "a -1 at zero was taken: %r" % o["under"])
        self.assertEqual(o["under"]["refused"], "below-zero", o["under"])
        self.assertEqual(o["afterUnder"]["ber"], 0)
        self.assertEqual(sum(1 for c in o["callsHand"] if c[2] < 0), 1, "a refused -1 still moved the door")

    def test_the_add_box_lists_a_count_as_its_tally_row(self):
        o = self.o
        r = o["row"]
        self.assertTrue(r["hasRow"] and r["minus"] and r["plus"], "a typed rune is not its tally's row with -1 / +1: %r" % r)
        self.assertIn("Ber Rune|0", r["tallies"], r)
        self.assertTrue(o["take"]["ok"] and o["enter"]["ok"], (o["take"], o["enter"]))
        self.assertEqual(o["afterBox"]["ber"], 2, "the row's +1 and Enter did not each move the tally")
        self.assertEqual(o["callsBox"], [["adjustRuneStash", "Ber", 1], ["adjustRuneStash", "Ber", 1]], o["callsBox"])

    def test_the_read_chip_asks_the_same_door(self):
        self.assertEqual(self.o["callsChip"], [["adjustGemStash", "Perfect Amethyst", 1]],
                         "the TV read chip moved the gem without the Gem Stash's door: %r" % self.o["callsChip"])
        self.assertEqual(self.o["afterChip"]["ame"], 2)
        self.assertEqual(self.o["ownedAfter"], 0)

    def test_no_second_counter_writes_a_tally_by_one(self):
        code = _code()
        hits = re.findall(r"(?:runeStash|gemStash|materialStash)\[[^\]]+\]\s*=\s*\(parseInt\([^)]*\)\s*\|\|\s*0\)\s*\+\s*1", code)
        self.assertEqual(hits, [], "a store is moved by one outside its door: %r" % hits)


RED_PROOF = [
    {"why": "REG-3004 - the hand door refuses a count again instead of moving its tally",
     "file": "bible.html",
     "find": "    if (!pre.ok && pre.stash && typeof window._stashTallyMove === 'function')\n",
     "replace": "    if (false)\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3004 - the count move writes the store itself, beside the Tools tab's door",
     "file": "bible.html",
     "find": "    door(key, d);\n    var now = count(key);\n",
     "replace": "    if (t.kind === 'rune') { runeStash[key] = was + d; persist(); } else door(key, d);\n    var now = count(key);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3004 - a -1 at zero is taken",
     "file": "bible.html",
     "find": "    if (was + d < 0)\n      return { ok: false, refused: 'below-zero',",
     "replace": "    if (false)\n      return { ok: false, refused: 'below-zero',",
     "matches": 1, "needs": "node"},
    {"why": "REG-3004 - + Add an item lists no tally row for a typed count",
     "file": "bible.html",
     "find": "    if (String(q || '').trim()) _talOf(String(q).trim(), true);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3004 - the read chip's +1 writes the gem store itself again (a second counter)",
     "file": "bible.html",
     "find": "      else if(kind==='gem'){ if(typeof window.adjustGemStash==='function') window.adjustGemStash(key, 1); else return; }",
     "replace": "      else if(kind==='gem'){ gemStash[key]=(parseInt(gemStash[key],10)||0)+1; persist(); if(typeof renderGemStash==='function') renderGemStash(); }",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
