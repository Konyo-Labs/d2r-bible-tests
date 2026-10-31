# -*- coding: utf-8 -*-
"""REG-3068 (GrokBot 05:07, #230) - ENTER TAKES THE EXACT NAME, NEVER THE TOP ROW BY GUESS.

GrokBot on his board: Vault -> "or add by name only" -> type "Spirit" -> the list is [Cerebus' Bite, Ravenlore, Spirit,
Spirit Forge, ...] and ENTER ADDED Cerebus' Bite, the top row. "Oath" lists [Bane's Oathmaker (sword), Oath] and Enter
would have taken the sword. Now, in the add box:
  * Enter takes the row whose name IS what he typed (case-insensitive; a trailing "(alias)" aside);
  * a name that is two items is asked, and nothing is added;
  * with no exact name Enter takes nothing until he picks a row;
  * a count he names exactly is its tally's +1 (REG-3004 kept: "Ber" is the Rune Stash's Ber Rune row).
Swept: the Tools tab's tally search ticked its top hit on Enter - the same guess - and now ticks only an exact name.
The Keepers box was fixed by REG-3000. FIND and the planner have no Enter that picks a row (FIND's box answers Escape,
the planner opens on input), the d2jsp find box filters, and the builder's mod picker takes the marked option. The
global search and the command palette open their highlighted row - navigation, not an add - and are named, not changed.
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
function enter(q){
  var qi = document.getElementById('vault-hand-q'); qi.value = q; W.vaultHandSearch(q);
  var list = (W._vhKeep || []).map(function(r){ return r.as; });
  var before = Array.from(owned).sort();
  var r = W._vaultHandKey({ key: 'Enter', preventDefault: function(){} });
  var after = Array.from(owned).filter(function(n){ return before.indexOf(n) < 0; });
  return { top: list[0] || null, list: list.slice(0, 6), res: r && { ok: r.ok, mode: r.mode, name: r.name, refused: r.refused, among: r.among },
           added: after, say: String((document.getElementById('vault-hand-say') || {}).textContent || '') };
}
W.vaultHandOpen();
OUT.spirit = enter('Spirit');
OUT.oath = enter('oath');
OUT.spir = enter('Spir');
OUT.ber = enter('Ber');
OUT.berCount = (W.runeStash || {})['Ber'] || 0;
/* a name that is two items here */
W._vhKeep = [{ id: 'k1', name: 'Twin', as: 'Twin (sword)' }, { id: 'k2', name: 'Twin', as: 'Twin' }]; W._vhTal = [];
document.getElementById('vault-hand-q').value = 'twin';
var tw = W._vaultHandKey({ key: 'Enter', preventDefault: function(){} });
OUT.twin = tw && { ok: tw.ok, refused: tw.refused, among: tw.among };
W.vaultHandClose();
/* the Tools tab's tally search: its Enter, on rows the search drew */
function stubBox(names){
  var clicked = [], say = { textContent: '' };
  var rows = names.map(function(n){ var go = { click: function(){ clicked.push(n); } };
    return { querySelector: function(s){ return s === '.tsrch-nm' ? { textContent: n } : s === '.tsrch-go' ? go : null; } }; });
  var box = { querySelectorAll: function(s){ return s === '.tsrch-row' ? rows : []; }, querySelector: function(s){ return s === '.tsrch-n' ? say : null; } };
  return { box: box, clicked: clicked, say: say };
}
function tally(names, q){ var b = stubBox(names); var inp = { value: q, closest: function(){ return b.box; } };
  W._tallySearchKey({ key: 'Enter', preventDefault: function(){} }, inp); return { clicked: b.clicked, say: b.say.textContent }; }
OUT.tsSpirit = tally(['Cerebus’ Bite', 'Ravenlore', 'Spirit Forge', 'Spirit'], 'spirit');
OUT.tsNone = tally(['Spirit Forge', 'Spirit Keeper'], 'Spir');
OUT.tsTwo = tally(['Gull', 'Gull'], 'gull');
})();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class EnterTakesTheExactNameNeverTheTopRow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=SEED, timeout=300)

    def test_spirit_takes_spirit_not_the_top_row(self):
        s = self.o["spirit"]
        self.assertNotEqual(s["top"], "Spirit", "PREMISE: the top row is already Spirit, so this case proves nothing: %r" % s)
        self.assertIn("Spirit", s["list"], s)
        self.assertEqual((s["res"]["ok"], s["res"]["name"]), (True, "Spirit"), "Enter took another row: %r" % s)
        self.assertEqual(s["added"], ["Spirit"], "Enter added another item: %r" % s["added"])

    def test_oath_takes_oath_not_the_sword(self):
        o = self.o["oath"]
        self.assertEqual(o["top"], "Bane's Oathmaker (sword)", "PREMISE: the sword is not the top row: %r" % o)
        self.assertEqual(o["res"]["name"], "Oath", o)
        self.assertNotIn("Bane's Oathmaker (sword)", o["added"], o)

    def test_no_exact_name_takes_nothing(self):
        s = self.o["spir"]
        self.assertTrue(s["list"], "PREMISE: 'Spir' lists rows: %r" % s)
        self.assertEqual((s["res"]["ok"], s["res"]["refused"]), (False, "no-exact"), s)
        self.assertEqual(s["added"], [], "Enter added a row by guess: %r" % s["added"])
        self.assertIn("exactly", s["say"], s)

    def test_a_name_that_is_two_items_is_asked(self):
        self.assertEqual((self.o["twin"]["ok"], self.o["twin"]["refused"]), (False, "ambiguous"), self.o["twin"])
        self.assertEqual(sorted(self.o["twin"]["among"]), ["Twin", "Twin (sword)"], self.o["twin"])

    def test_an_exact_count_is_its_tally_row(self):
        b = self.o["ber"]
        self.assertEqual((b["res"]["ok"], b["res"]["mode"], b["res"]["name"]), (True, "tallied", "Ber Rune"), b)
        self.assertEqual(self.o["berCount"], 1, "Enter on 'Ber' did not move the Rune Stash's Ber by one")
        self.assertEqual(b["added"], [], b)

    def test_the_tools_tally_search_ticks_only_an_exact_name(self):
        self.assertEqual(self.o["tsSpirit"]["clicked"], ["Spirit"], "Enter ticked another row than the exact one: %r" % self.o["tsSpirit"])
        self.assertEqual(self.o["tsNone"]["clicked"], [], "Enter ticked a row by guess: %r" % self.o["tsNone"])
        self.assertIn("exactly", self.o["tsNone"]["say"])
        self.assertEqual(self.o["tsTwo"]["clicked"], [], "Enter ticked one of two rows with the same name")


RED_PROOF = [
    {"why": "REG-3068 - the add box's Enter takes the top row again",
     "file": "bible.html",
     "find": "    var _ex = _vhExact(_q);\n",
     "replace": "    var _ex = (window._vhKeep || []).slice(0, 1).map(function(r){ return { id: r.id, name: r.as }; });\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3068 - a name that is two items is taken without asking",
     "file": "bible.html",
     "find": "    if (_ex.length === 1) return _ex[0].tally ?",
     "replace": "    if (_ex.length >= 1) return _ex[0].tally ?",
     "matches": 1, "needs": "node"},
    {"why": "REG-3068 - Enter takes a row whose name merely contains what he typed (the exact rule gone)",
     "file": "bible.html",
     "find": "      if ([r.as, r.name].some(function(n){ return fold(n) === fq || bare(n) === fq; })){ seen[r.as] = 1; out.push({ id: r.id, name: r.as }); }",
     "replace": "      if ([r.as].some(function(n){ return fold(n).indexOf(fq) >= 0; })){ seen[r.as] = 1; out.push({ id: r.id, name: r.as }); }",
     "matches": 1, "needs": "node"},
    {"why": "REG-3068 - an exact count loses its tally row on Enter (REG-3004 broken)",
     "file": "bible.html",
     "find": "    (window._vhTal || []).forEach(function(t){ if (t.exact && !seen['\\u0000' + t.name]){",
     "replace": "    (window._vhTal || []).forEach(function(t){ if (false && t.exact && !seen['\\u0000' + t.name]){",
     "matches": 1, "needs": "node"},
    {"why": "REG-3068 - the Tools tally search ticks its top hit on Enter again",
     "file": "bible.html",
     "find": "      if (ex.length === 1){ var go = ex[0].querySelector('.tsrch-go'); if (go) go.click(); return; }",
     "replace": "      var _r0 = box.querySelectorAll('.tsrch-row')[0]; if (_r0){ var go = _r0.querySelector('.tsrch-go'); if (go) go.click(); return; }",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
