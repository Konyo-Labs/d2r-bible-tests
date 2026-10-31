# -*- coding: utf-8 -*-
"""REG-2857 (router probe, GrokBot's v3829 Vault pass) - A RUNE OR A GEM IS NAMED FOR WHAT IT IS, NEVER "NOTHING ON THE BOARD
RECOGNISES THIS NAME".

Measured on the whole page in node before the fix: suggestMule('Ber') and suggestMule('Perfect Amethyst') answered Unsorted
with "nothing on the board recognises this name", while "Ber Rune" answered the shared stash (never a mule), RUNES names all
33 runes, GEM_TYPES all 35 gems, and the Rune Stash and Gem Stash on the Tools tab count them. The hand door refused both
with the sentence for any name the vault does not draw.

  * a bare rune name is the same item as "<rune> Rune": SHARED_STASH_RE matches the whole name, so the router, the dock, the
    records and the console doctor (which reads that one line) give both one answer; its rune list is held equal to RUNES;
  * a gem stayed Unsorted then (the gem ruling was open) and said it is a gem the Gem Stash counts; since his 2026-10-28
    words (REG-2899) a gem is a count on the shared stash's line like a rune, and the register door refuses it;
  * the hand door names the stash that counts it and owns nothing (since REG-3004 it moves that stash's tally);
  * a base named Rune Sword / Rune Bow and the unique Rune Master are not runes.

Driven on the whole page in node (vault_page_node), fixtures only; the console doctor's half in Python. RED_PROOF below.
"""
import io
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
OUT.runes = RUNES.map(function(r){ return r.n; });
OUT.gems = [];
GEM_TYPES.forEach(function(t){ t.q.forEach(function(g){ OUT.gems.push(g.name); }); });
OUT.runeShared = OUT.runes.filter(function(n){ return !W.isSharedStash(n) || W.suggestMule(n) !== null; });
OUT.notRunes = ['Rune Sword', 'Rune Bow', 'Rune Master', 'Hellfire Torch'].filter(function(n){ return W.isSharedStash(n); });
OUT.ber = { sg: W.suggestMule('Ber'), rune: W.suggestMule('Ber Rune'), prop: W.vaultPropose('Ber') };
OUT.gemAnswers = OUT.gems.map(function(n){ var s = W.suggestMule(n); return [n, s && s.id, !!(s && s.unsorted), s && s.why]; });
OUT.gemProp = W.vaultPropose('Perfect Amethyst');
OUT.gemShared = OUT.gems.filter(function(n){ return !W.isSharedStash(n); });
var before = Array.from(owned).length;
OUT.hand = {};
['Ber', 'Jah', 'Perfect Amethyst'].forEach(function(n){ var a = W.vaultHandAdd(n, null, {}); OUT.hand[n] = a && { ok: a.ok, mode: a.mode, kind: a.kind, refused: a.refused, why: a.why }; });
OUT.handAdded = Array.from(owned).length - before;
W._vaultAutoIntakeSet && W._vaultAutoIntakeSet(true);
var g = W.tvVaultRegister('Perfect Amethyst', { by: 'hand', at: new Date().toISOString(), where: 'the law' });
OUT.reg = g && { refused: g.refused, why: g.why };
/* the register door's no-home answer carries the router's own Unsorted reason (REG-2857's sweep): a name nothing knows */
var v = W.tvVaultRegister('Bone Visor', { by: 'hand', at: new Date().toISOString(), where: 'the law' });
OUT.regUnsorted = v && { refused: v.refused, why: v.why };
})();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ARuneOrAGemIsNamedNeverUnrecognised(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=SEED, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(len(self.o["runes"]), 33, "PREMISE: RUNES is not the 33 runes: %r" % self.o["runes"])
        self.assertEqual(len(self.o["gems"]), 35, "PREMISE: GEM_TYPES is not the 35 gems")

    def test_a_bare_rune_name_is_the_same_item_as_its_rune(self):
        self.assertEqual(self.o["runeShared"], [], "bare rune names that are not the shared stash: %r" % self.o["runeShared"])
        self.assertIsNone(self.o["ber"]["sg"], "'Ber' was answered %r" % self.o["ber"]["sg"])
        self.assertIsNone(self.o["ber"]["rune"], "'Ber Rune' was answered %r" % self.o["ber"]["rune"])
        self.assertEqual(self.o["ber"]["prop"]["kind"], "shared", self.o["ber"]["prop"])
        self.assertEqual(self.o["notRunes"], [], "a base or a unique was read as a rune: %r" % self.o["notRunes"])

    def test_the_regex_rune_list_is_runes(self):
        with io.open(PAGE, encoding="utf-8") as fh:
            s = fh.read()
        m = re.findall(r"var SHARED_STASH_RE = /.*?\|\^\\s\*\(\?:([a-z|]+)\)\\s\*\$\|", s)
        self.assertEqual(len(m), 1, "the bare-rune alternation is not in SHARED_STASH_RE exactly once")
        self.assertEqual(m[0].split("|"), [n.lower() for n in self.o["runes"]],
                         "the regex's rune list drifted from RUNES")

    def test_a_gem_says_it_is_a_gem_everywhere(self):
        # REG-2899 (his words 2026-10-28) - a gem is a count in the Gem Stash, never a vault item: no longer Unsorted, the
        # shared stash's own area, at the router, the proposal and the register door (which now refuses it)
        self.assertEqual(self.o["gemShared"], [], "gems the shared-stash line does not answer: %r" % self.o["gemShared"])
        for n, gid, uns, why in self.o["gemAnswers"]:
            self.assertIsNone(gid, "%s was given a mule: %r" % (n, gid))
            self.assertFalse(uns, "%s is Unsorted again: %r" % (n, why))
        self.assertIn("counted in the Gem Stash", self.o["gemProp"]["why"], self.o["gemProp"])
        self.assertEqual((self.o["reg"] or {}).get("refused"), "not-an-item", "the register door owned a gem: %r" % self.o["reg"])
        self.assertIn("Gem Stash", (self.o["reg"] or {}).get("why") or "", self.o["reg"])

    def test_the_register_door_carries_the_routers_reason(self):
        r = self.o["regUnsorted"] or {}
        self.assertEqual(r.get("refused"), "no-home", r)
        self.assertIn("nothing on the board recognises this name", r.get("why") or "",
                      "the register door does not carry the router's Unsorted reason: %r" % r)

    def test_the_hand_door_names_the_stash_that_counts_it(self):
        h = self.o["hand"]
        # REG-3004 (his Q5): the hand door moves the stash's own tally (and names it) instead of refusing - and owns nothing
        for n, kind, where in (("Ber", "rune", "Rune Stash"), ("Jah", "rune", "Rune Stash"), ("Perfect Amethyst", "gem", "Gem Stash")):
            self.assertTrue(h[n]["ok"] and h[n]["mode"] == "tallied", h[n])
            self.assertEqual(h[n]["kind"], kind, h[n])
            self.assertIn(where, h[n]["why"], h[n])
        self.assertEqual(self.o["handAdded"], 0, "a rune or gem reached his owned list")

    def test_the_console_doctor_reads_the_same_rune(self):
        import console_doctor as C
        route = C._vault_route_fn()
        self.assertTrue(route.readable, "the console doctor could not read SHARED_STASH_RE")
        self.assertIs(route("Ber")[0], False, "the console doctor routes a bare rune to a mule")
        self.assertIs(route("Rune Sword")[0], True, "the console doctor reads Rune Sword as a rune")


RED_PROOF = [
    {"why": "REG-2857 - a bare rune name is a name nothing recognises again (Ber -> Unsorted)",
     "file": "bible.html",
     "find": "|^\\s*(?:el|eld|tir|nef|eth|ith|tal|ral|ort|thul|amn|sol|shael|dol|hel|io|lum|ko|fal|lem|pul|um|mal|ist|gul|vex|ohm|lo|sur|ber|jah|cham|zod)\\s*$",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2857 / REG-2899 - a gem is not the shared-stash line's again (a name nothing recognises)",
     "file": "bible.html",
     "find": "|^\\s*(?:(?:chipped|flawed|flawless|perfect)\\s+)?(?:amethyst|diamond|emerald|ruby|sapphire|topaz|skull)\\s*$",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2857 - the hand door refuses a rune or a gem without saying which stash counts it",
     "file": "bible.html",
     "find": "      if (_cnt) return { ok: false, refused: 'not-drawn', stash: _cnt.kind,",
     "replace": "      if (false) return { ok: false, refused: 'not-drawn', stash: _cnt.kind,",
     "matches": 1, "needs": "node"},
    {"why": "REG-2857 - the register door drops the router's Unsorted reason again",
     "file": "bible.html",
     "find": "        _vf = { ok: false, refused: 'no-home', why: (sg && sg.unsorted && typeof sg.why === 'string' && sg.why.trim())\n",
     "replace": "        _vf = { ok: false, refused: 'no-home', why: false && (sg && sg.unsorted && typeof sg.why === 'string' && sg.why.trim())\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
