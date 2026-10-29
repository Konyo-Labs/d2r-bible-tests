# -*- coding: utf-8 -*-
"""REG-2858 (router probe, GrokBot's v3829 Vault pass) - A BARE "SHAKO" THROUGH THE HAND DOOR IS ASKED, NEVER GUESSED.

"Shako" is a white base, and it is also the name the board files Harlequin Crest under ("Harlequin Crest (Shako)").
Measured on the whole page in node before the fix: vaultHandAdd('Shako') owned a white Shako base (the router then sends it
to SOCKETED, "white base - still needed for Lore, Nadir") without a word, when he may mean his Harlequin Crest. His rule: a
doubt becomes a question, never a guess.

  * a bare base the board also files a unique under is refused 'ambiguous', naming both, and nothing is added;
  * the planner row's kind answers it: 'unique' owns Harlequin Crest (Shako), 'base' owns the white Shako;
  * an Eth / Superior word settles it as the base, and a base no unique is filed under (Monarch, Archon Plate; Dagger,
    whose "Gull (dagger)" bracket is a slot note) is added
    as before - so the hand door's base adds (test_vault_l1_a_hand_add_routes_by_type) keep working;
  * the pairs are read from the catalogue: on v3833 there is exactly one, Shako.

REG-3075 (GrokBot v3838, #230) - AND THE + ADD AN ITEM BOX ASKS IT TOO. Its Enter took the top row, so "Shako" + Enter filed
Harlequin Crest (Shako) as the unique without a word (reproduced on v3838's page in node: the row list is [Harlequin Crest,
then the white Shako the box does not draw], and Enter took the first). REG-3068's exact-name Enter stopped the guess but
did not ask - "no item is named exactly Shako; pick one from the list". Now the box's Enter asks the door's own question
(one helper, _vhTwinAsk) before any row is taken, with its two answers as buttons: the unique's row, and the white base's
row, which the box takes as the base.

Driven on the whole page in node (vault_page_node), fixtures only. RED_PROOF below.
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
function add(n, o){ var a = W.vaultHandAdd(n, null, o || {}); return a && { ok: a.ok, refused: a.refused || null, mode: a.mode || null,
                                                                           name: a.name || null, among: a.among || null, why: a.why || '' }; }
OUT.pairs = [];
ITEMS.forEach(function(i){
  var p = /^(.+) \(([^()]+)\)$/.exec(String((i && i.n) || ''));
  if (p && W._vaultHandBase(p[2]) === p[2]) OUT.pairs.push(i.n);
});
OUT.bare = add('Shako');
OUT.lower = add('shako');
OUT.ownedAfterAsk = Array.from(owned).filter(function(n){ return /shako/i.test(n); });
OUT.superior = add('Superior Shako');
OUT.monarch = add('Monarch');
OUT.archon = add('Archon Plate');
OUT.dagger = add('Dagger');
OUT.unique = add('Shako', { kind: 'unique' });
OUT.base = add('Shako', { kind: 'base' });
OUT.owned = Array.from(owned).sort();
})();
"""


BOX = r"""
(function(){
var W = window;
function enter(q){
  var qi = document.getElementById('vault-hand-q'); qi.value = q; W.vaultHandSearch(q);
  var before = Array.from(owned).sort();
  var r = W._vaultHandKey({ key: 'Enter', preventDefault: function(){} });
  var say = document.getElementById('vault-hand-say');
  return { rows: ((W._vhCat || {}).rows || []).map(function(x){ return x.name + '/' + x.q; }), top: ((W._vhKeep || [])[0] || {}).as || null,
           res: r && { ok: r.ok, refused: r.refused || null, among: r.among || null, choices: r.choices || null },
           added: Array.from(owned).filter(function(n){ return before.indexOf(n) < 0; }),
           say: String(say.innerHTML || ''), state: say.getAttribute('data-state') };
}
function take(id){ var before = Array.from(owned); var r = W.vaultHandTake(id);
  return { ok: !!(r && r.ok), mode: r && r.mode || null, refused: r && r.refused || null,
           added: Array.from(owned).filter(function(n){ return before.indexOf(n) < 0; }) }; }
W.vaultHandOpen();
OUT.enter = enter('Shako');
OUT.upper = enter('SHAKO');
OUT.base = take((OUT.upper.res.choices || [])[1]);
OUT.again = enter('Shako');
OUT.unique = take((OUT.again.res.choices || [])[0]);
OUT.owned = Array.from(owned).sort();
})();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ABareShakoIsAskedNotGuessed(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=SEED, timeout=300)
        cls.box = VPN.run(BOX, prelude=SEED, timeout=300)

    def test_the_page_booted_and_the_catalogue_names_the_pair(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["pairs"], ["Harlequin Crest (Shako)"],
                         "PREMISE: the uniques filed under a hand-door base changed: %r" % self.o["pairs"])

    def test_a_bare_shako_is_asked_and_nothing_is_added(self):
        for k in ("bare", "lower"):
            r = self.o[k]
            self.assertFalse(r["ok"], "a bare Shako was owned without asking (%s): %r" % (k, r))
            self.assertEqual(r["refused"], "ambiguous", r)
            self.assertEqual(r["among"], ["Harlequin Crest (Shako)", "Shako"], r)
            self.assertIn("Which one?", r["why"], r)
            self.assertIn("Nothing was added", r["why"], r)
        self.assertEqual(self.o["ownedAfterAsk"], [], "a question still added something: %r" % self.o["ownedAfterAsk"])

    def test_the_kind_answers_the_question(self):
        self.assertTrue(self.o["unique"]["ok"], self.o["unique"])
        self.assertEqual(self.o["unique"]["name"], "Harlequin Crest (Shako)", self.o["unique"])
        self.assertTrue(self.o["base"]["ok"], self.o["base"])
        self.assertEqual(self.o["base"]["name"], "Shako", self.o["base"])
        self.assertIn("Harlequin Crest (Shako)", self.o["owned"])
        self.assertIn("Shako", self.o["owned"])

    def test_the_add_box_enter_asks_and_takes_nothing(self):
        for k in ("enter", "upper"):
            e = self.box[k]
            self.assertEqual(e["top"], "Harlequin Crest (Shako)", "PREMISE: the box's top row for Shako moved: %r" % e)
            self.assertIn("Shako/b", e["rows"], "PREMISE: the white Shako is not among the box's rows: %r" % e["rows"])
            self.assertEqual(e["added"], [], "Enter on a bare Shako filed something without asking (%s): %r" % (k, e))
            self.assertEqual((e["res"]["refused"], e["res"]["among"]), ("ambiguous", ["Harlequin Crest (Shako)", "Shako"]),
                             "Enter on a bare Shako did not ask the door's question (%s): %r" % (k, e["res"]))
            self.assertEqual(e["state"], "ask", e)
            self.assertIn("Which one?", e["say"])
            self.assertEqual(e["say"].count('class="vault-btn vh-choice"'), 2, "the question has no answers to press: %r" % e["say"])

    def test_the_box_answers_take_the_base_and_the_unique(self):
        b, u = self.box["base"], self.box["unique"]
        self.assertEqual((b["ok"], b["added"]), (True, ["Shako"]), "the white-base answer did not add the base: %r" % b)
        self.assertEqual(self.box["again"]["res"]["refused"], "ambiguous", "owning the base settled the next bare Shako by guess")
        self.assertEqual((u["ok"], u["added"]), (True, ["Harlequin Crest (Shako)"]), "the unique answer did not add it: %r" % u)
        self.assertEqual(self.box["owned"], ["Harlequin Crest (Shako)", "Shako"])

    def test_a_base_no_unique_is_filed_under_is_added_as_before(self):
        for k, nm in (("superior", "Superior Shako"), ("monarch", "Monarch"), ("archon", "Archon Plate"), ("dagger", "Dagger")):
            self.assertTrue(self.o[k]["ok"], "%s was refused: %r" % (nm, self.o[k]))
            self.assertEqual(self.o[k]["name"], nm, self.o[k])


RED_PROOF = [
    {"why": "REG-2858 - a bare Shako is owned as a white base again, never asked",
     "file": "bible.html",
     "find": "    else if (_tw && _kd !== 'base') return _tw.res;\n",
     "replace": "    else if (false) return _tw.res;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2858 - the planner's 'unique' kind does not answer the question (the unique cannot be added by its base)",
     "file": "bible.html",
     "find": "    if (_tw && _tw.twins.length === 1 && _kd === 'unique') r = { ok: true, name: _tw.twins[0] };\n",
     "replace": "    if (false) r = { ok: true, name: _tw.twins[0] };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2858 - the pair is read off any bracket, so a lowercase slot note asks too (Dagger)",
     "file": "bible.html",
     "find": "          if (p && _vaultHandBase(p[2]) === p[2] && _vaultKeeps(i.n)) (m[p[2]] = m[p[2]] || []).push(String(i.n));\n",
     "replace": "          if (p && _vaultHandBase(p[2]) && _vaultKeeps(i.n)) (m[_vaultHandBase(p[2])] = m[_vaultHandBase(p[2])] || []).push(String(i.n));\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3075 - the add box's Enter does not ask: a bare Shako is refused 'no exact name' (or, before REG-3068, took the top row)",
     "file": "bible.html",
     "find": "    var _tw = _q ? _vhTwinAsk(_q, _q) : null;\n",
     "replace": "    var _tw = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3075 - the box's white-base answer is asked again (a base row he picks is not the base)",
     "file": "bible.html",
     "find": "    var _rk = row ? (_VH_KIND[row.q] || (row.q === 'b' ? 'base' : null)) : null;\n",
     "replace": "    var _rk = row ? (_VH_KIND[row.q] || null) : null;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
