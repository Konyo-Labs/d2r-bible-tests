# -*- coding: utf-8 -*-
"""REG-2899 (his words 2026-10-28 ~20:40) - A RUNE, A GEM, A MATERIAL OR A REJUVENATION POTION IS A COUNT IN ITS OWN TALLY,
NEVER A VAULT ITEM WITH A MULE CELL.

His words: "gems will eventually move to the shared stash so they are not relevant when seen in inventory/stash they have
their own designated area runes/gems/materials/rejuvination potions they are automatically going to go to the ingame
designated area we also have those same templates already designed in the console with their tallies".

Measured on the whole page in node before the fix: a gem was Unsorted (REG-2857 said "a gem the Gem Stash counts" but
kept no home), a rejuvenation potion and a key named nothing at the router, "Key of Terror" was OWNED through + Add an
item (a catalogue lists it), and the register door owned runes and gems it read. Now one rule (_stashTallyOf, from the
board's own tables - RUNES, GEM_TYPES, MAT_TAB_LAYOUT) says which tally counts it, and every door reads it:
  * the router answers the shared stash (its own area), never a mule and never Unsorted; the proposal says which tally;
  * the hand door owns nothing - even a catalogue-listed key; it moves that tally instead (REG-3004, his Q5);
  * the register door refuses it (a rune, a gem, a rejuvenation potion; a material in its own words, REG-158.4);
  * SHARED_STASH_RE's gem and Materials-tab names equal the tables, and the console doctor reads the same line;
  * a Sunder charm (a unique the vault keeps) and Rune Sword (a base) are not counts.

Driven on the whole page in node (vault_page_node), fixtures only; the console doctor's half in Python. RED_PROOF below.
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

SEED = "localStorage.setItem('d2r_ownerClaim', '*');\n"
BODY = r"""
(function(){
var W = window;
var mats = [].concat.apply([], [].concat(MAT_TAB_LAYOUT.left, MAT_TAB_LAYOUT.right));
OUT.mats = mats;
OUT.matNotShared = mats.filter(function(n){ return !W.isSharedStash(n); });
OUT.matNoTally = mats.filter(function(n){ return !W._stashTallyOf(n); });
var gems = []; GEM_TYPES.forEach(function(t){ t.q.forEach(function(g){ gems.push(g.name); }); });
OUT.gemNoTally = gems.filter(function(n){ return !W._stashTallyOf(n) || W._stashTallyOf(n).kind !== 'gem'; });
OUT.kinds = {};
['Ber', 'Perfect Ruby', "Baal's Eye", 'Full Rejuvenation Potion', 'Rejuvenation Potion', 'Key of Hate', 'Bone Break', 'Rune Sword'].forEach(function(n){
  var t = W._stashTallyOf(n), s = W.suggestMule(n), p = W.vaultPropose(n);
  OUT.kinds[n] = { kind: t ? t.kind : null, sg: s ? s.id : null, unsorted: !!(s && s.unsorted), prop: p ? p.kind + ' | ' + p.why : null };
});
var before = Array.from(owned).length;
OUT.hand = {};
['Key of Terror', 'Full Rejuvenation Potion', "Mephisto's Brain"].forEach(function(n){ var a = W.vaultHandAdd(n, null, {}); OUT.hand[n] = a && { ok: a.ok, mode: a.mode, refused: a.refused, kind: a.kind, why: a.why }; });
OUT.handAdded = Array.from(owned).length - before;
W._vaultAutoIntakeSet && W._vaultAutoIntakeSet(true);
OUT.reg = {};
['Ist Rune', 'Flawless Topaz', 'Partial Rejuvenation Potion'].forEach(function(n){
  var g = W.tvVaultRegister(n, { by: 'hand', at: new Date().toISOString(), where: 'the law' }); OUT.reg[n] = g && { ok: g.ok, refused: g.refused, why: g.why }; });
OUT.ownedAfter = Array.from(owned).sort();
})();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ARuneGemMaterialOrRejuvIsACount(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=SEED, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertGreaterEqual(len(self.o["mats"]), 20, "PREMISE: the Materials tab layout was not read: %r" % self.o["mats"])

    def test_every_tally_name_is_on_the_shared_stash_line_and_named_by_the_rule(self):
        self.assertEqual(self.o["matNotShared"], [], "Materials-tab names the shared-stash line misses: %r" % self.o["matNotShared"])
        self.assertEqual(self.o["matNoTally"], [], "Materials-tab names the tally rule cannot name: %r" % self.o["matNoTally"])
        self.assertEqual(self.o["gemNoTally"], [], "gems the tally rule cannot name: %r" % self.o["gemNoTally"])

    def test_the_router_answers_the_tally_never_a_mule_never_unsorted(self):
        want = {"Ber": "rune", "Perfect Ruby": "gem", "Baal's Eye": "material", "Full Rejuvenation Potion": "rejuv",
                "Rejuvenation Potion": "rejuv", "Key of Hate": "material"}
        for n, kind in want.items():
            k = self.o["kinds"][n]
            self.assertEqual(k["kind"], kind, "%s: %r" % (n, k))
            self.assertIsNone(k["sg"], "%s was given a mule: %r" % (n, k))
            self.assertFalse(k["unsorted"], "%s is Unsorted: %r" % (n, k))
            self.assertTrue(k["prop"].startswith("shared | ") and "counted in the" in k["prop"], "%s: %r" % (n, k))
        for n in ("Bone Break", "Rune Sword"):
            self.assertIsNone(self.o["kinds"][n]["kind"], "%s was read as a count: %r" % (n, self.o["kinds"][n]))

    def test_the_hand_door_owns_no_count(self):
        # REG-3004 (his Q5): the hand door moves the count's own tally instead of refusing it - and still owns nothing
        for n, a in self.o["hand"].items():
            self.assertTrue(a["ok"] and a["mode"] == "tallied", "%s did not move its tally: %r" % (n, a))
            self.assertIn(a["kind"], ("material", "rejuv"), a)
            self.assertIn("the Materials stash", a["why"], a)
        self.assertEqual(self.o["handAdded"], 0, "a count reached his owned list")

    def test_the_register_door_owns_no_count(self):
        for n, g in self.o["reg"].items():
            self.assertEqual(g["refused"], "not-an-item", "%s was registered: %r" % (n, g))
            self.assertIn("counted in the", g["why"], g)
        for n in self.o["reg"]:
            self.assertNotIn(n, self.o["ownedAfter"])

    def test_the_console_doctor_reads_the_same_line(self):
        import console_doctor as C
        route = C._vault_route_fn()
        self.assertTrue(route.readable)
        for n in ("Perfect Amethyst", "Full Rejuvenation Potion", "Key of Terror", "Diablo’s Horn"):
            self.assertIs(route(n)[0], False, "the console doctor routes %s to a mule" % n)
        self.assertIs(route("Shimmering Small Charm")[0], True)


RED_PROOF = [
    {"why": "REG-2899 - keys, organs, the Token and rejuvenation potions are off the shared-stash line again",
     "file": "bible.html",
     "find": "|^\\s*(?:key of (?:terror|hate|destruction)|diablo['’]s horn|baal['’]s eye|mephisto['’]s brain|token of absolution|(?:full |partial )?rejuvenation potion)\\s*$",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2899 - the tally rule does not read the Materials tab",
     "file": "bible.html",
     "find": "    var hit = _TALLY_MAT[fold(nm)];\n",
     "replace": "    var hit = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2899 - the hand door asks the tally rule only after the catalogue (Key of Terror owned again)",
     "file": "bible.html",
     "find": "    {   /* REG-2857 a rune or a gem says which stash counts it; REG-2899 - asked FIRST:",
     "replace": "    if (!_vaultKeeps(r.name) && !_vaultHandBase(r.name)){   /* REG-2857 a rune or a gem says which stash counts it; REG-2899 - asked FIRST:",
     "matches": 1, "needs": "node"},
    {"why": "REG-2899 - the register door owns a rune, a gem or a rejuvenation potion it reads again",
     "file": "bible.html",
     "find": "    if (_tl) return _tl + ' - nothing was registered';\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2899 - the proposal does not say which tally counts it",
     "file": "bible.html",
     "find": "    if (_tally) return _tally;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
