# -*- coding: utf-8 -*-
"""Front-run (REG-2839) - A MAGIC ITEM FROM THE PLANNER IS FILED ONCE, WITH ITS MODS, AND LEAVES NO TAKE-BACK.

A magic item's name is its mods. The planner filed the pick the moment the quality was chosen - the bare base, "Grand
Charm" - and the first mod renamed it, so every magic add took the bare base back through the removal door. Measured on
the whole page in node, 505 hand adds: all 20 batches the removal journal keeps (a ring of 20) were such take-backs
("Small Charm", "Amulet", "Grand Charm"); twenty magic adds push every real removal of his out of reach of the undo. Now
the planner holds a magic pick with no mod as a draft (REG-2832's hold) until Done files it once, with its mods; the plate
says Editing meanwhile. A rare keeps its rolled name as mods are added, so it still files at the pick; a magic pick he
leaves bare is still filed at Done. The filing door itself (vaultPlannerFile) is unchanged. RED_PROOF below.
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
var W = window, DB = W._cbDb();
function code(n){ return Object.keys(DB.b).find(function(c){ return DB.b[c][0] === n; }); }
function cur(){ var s = W._cbState(); return s && s.host && s.host.cur ? s.host.cur() : null; }
function journal(){ var l = W.vaultRemovalLog(); return Array.isArray(l) ? l.length : l; }
function plate(){ var h = String((document.getElementById('vault-planner-host') || {}).innerHTML || ''); var k = /<div class="vp-plate-k">([^<]*)<\/div>/.exec(h); return k ? k[1] : null; }
function owned_(){ return JSON.parse(W.LSR.getItem('d2r_owned') || '[]'); }
/* a magic Grand Charm, a prefix and a suffix */
W.vaultPlannerOpen(''); W._cbChoose('b:' + code('Grand Charm')); W._cbQuality('m'); H.flush(60, 3);
OUT.afterPick = { plate: plate(), owned: owned_(), journal: journal() };
var p = W._cbAffixPool(cur()).rows.p[0], s = W._cbAffixPool(cur()).rows.s[0];
W._cbAddMod(p[0]); W._cbAddMod(s[0]);
var e = cur(), name = W._cbShown(e, W._cbItem(e.id)).name;
W.vaultPlannerClose(); H.flush(60, 3);
OUT.done = { name: name, owned: owned_(), journal: journal(), mods: ((JSON.parse(W.LSR.getItem('d2r_magicFinds') || '{}')[name]) || {}).mods || null,
             undo: W._vaultUndo ? W._vaultUndo.what : null };
/* a magic pick he leaves bare is still filed, once, at Done */
W.vaultPlannerOpen(''); W._cbChoose('b:' + code('Small Charm')); W._cbQuality('m'); W.vaultPlannerClose(); H.flush(60, 3);
OUT.bare = { owned: owned_(), journal: journal() };
/* a rare files at the pick, as before */
W.vaultPlannerOpen(''); W._cbChoose('b:' + code('Ring')); W._cbQuality('rare'); H.flush(60, 3);
var re = cur(), rname = W._cbShown(re, W._cbItem(re.id)).name;
OUT.rare = { name: rname, plate: plate(), owned: owned_().indexOf(rname) >= 0 };
W.vaultPlannerClose(); H.flush(60, 3);
OUT.rareJournal = journal();
/* v3884 CI round - the dice never roll a real item's name: "Storm Eye" folds to Stormeye (the unique wand), so the Vault
   held the ring and it never filed (CI, e30ce54ee). Force the two words the dice would have picked. */
var rc = code('Ring'), P = W._cbRareWords(rc, 0), S = W._cbRareWords(rc, 1), R0 = Math.random, k = 0;
OUT.stormIdx = [P.indexOf('Storm'), S.indexOf('Eye')];
var seq = [(OUT.stormIdx[0] + 0.5) / P.length, (OUT.stormIdx[1] + 0.5) / S.length];
Math.random = function(){ return k < seq.length ? seq[k++] : R0(); };
try { OUT.forced = W._cbDice(rc); } finally { Math.random = R0; }
OUT.stormeye = DB.it.some(function(x){ return x[1] === 'Stormeye'; });
OUT.errors = H.errors.slice();
})();
"""


class AMagicPickFilesOnceWithItsMods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])

    def test_the_bare_magic_pick_is_a_draft(self):
        a = self.o["afterPick"]
        self.assertEqual(a["owned"], [], "the bare base was filed before its mods: %r" % a)
        self.assertEqual(a["plate"], "Editing", a)

    def test_done_files_it_once_with_its_mods_and_no_take_back(self):
        d = self.o["done"]
        self.assertEqual(d["owned"], [d["name"]], "the magic item was not filed once under its own name: %r" % d)
        self.assertEqual(len(d["mods"] or []), 2, "its mods were not kept: %r" % d)
        self.assertEqual(d["journal"], 0, "the add took a bare base back into the removal journal: %r" % d)
        self.assertNotIn("take-back", d["undo"] or "", d)

    def test_a_bare_magic_pick_is_still_filed_at_done(self):
        b = self.o["bare"]
        self.assertIn("Small Charm", b["owned"], "a magic pick he left bare was lost: %r" % b)
        self.assertEqual(b["journal"], 0, b)

    def test_a_rare_still_files_at_the_pick(self):
        r = self.o["rare"]
        self.assertTrue(r["owned"], "a rare is no longer filed at the pick: %r" % r)
        self.assertEqual(self.o["rareJournal"], 0)

    def test_a_rolled_rare_name_is_never_an_items_name(self):
        """v3884 CI round - "Storm Eye" is Stormeye with its space folded: the dice skip it, so the pick still files"""
        o = self.o
        self.assertTrue(o["stormeye"] and min(o["stormIdx"]) >= 0, "premise: Stormeye, Storm and Eye are not all in the data: %r" % o["stormIdx"])
        self.assertEqual(o["forced"][0], "Storm", "premise: the forced prefix was not rolled: %r" % o["forced"])
        self.assertNotEqual(" ".join(o["forced"]), "Storm Eye", "the dice rolled a real item's name (Stormeye)")


RED_PROOF = [
    {"why": "REG-2839 - the bare magic pick is filed at once again, and every magic add takes it back into the journal",
     "file": "bible.html",
     "find": "        if (entry && entry.q === 'm' && !(entry.affixes && entry.affixes.length)) return ctx.hold(entry);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "v3884 CI round - the dice roll a real item's name again (Storm Eye = Stormeye, so the ring never files)",
     "file": "bible.html",
     "find": "    var ok = s.filter(function(w){ return !_cbNameTaken[_cbNameFold(pw + w)]; });\n",
     "replace": "    var ok = s;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
