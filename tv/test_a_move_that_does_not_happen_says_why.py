# -*- coding: utf-8 -*-
"""REG-2854 - A MOVE THAT DOES NOT HAPPEN SAYS WHY, AND EVERY ANSWER OF THE VAULT'S MOVE DOOR IS RETURNED.

GrokBot's ACT-8 (#230, his MAGIC & RARE report 2026-10-28): "vaultAssign('Fine Small Charm of Vita','shared') returned
nothing and moved nothing". Measured on the whole page in node (tv/vault_page_node.py) before the fix:
  * an owned Magic & Rare keeper filed on the shared stash said "-> SHARED STASH" and returned undefined, while it stayed
    drawn in MAGIC & RARE and nowhere else: a rolled name is no record, so no other locker draws it, and a filing beside its
    keeper record is the double filing the integrity check takes back (REG-2184);
  * an unowned keeper was told it "is not on your owned list" - true, and not why;
  * a locker id the board does not have returned undefined and said nothing (the status kept the last move's words);
  * every filing that happened returned undefined too.
Now each refusal returns {ok:false, refused, why} and says it where he is looking (_vaultLockSay), a keeper's says what
it is, a filing returns {ok:true, mule}, and a unique, a set piece or a runeword sitting in Magic & Rare is filed as before.
Moving a keeper OUT of Magic & Rare (his charm ruling, ACT-4) is not decided here. RED_PROOF below.
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

MF = {"Fine Small Charm of Vita": {"q": "magic", "base": "Small Charm", "mods": [], "border": True},   # not owned
      "Stone Knot": {"q": "rare", "base": "Ring", "mods": []},                                         # owned
      "Nagelring": {"q": "unique", "base": "Ring"}}                                                    # a unique, owned
OWNED = ["Stone Knot", "Nagelring", "Harlequin Crest"]
PRELUDE = "localStorage.setItem('d2r_ownerClaim', '*');\n" + "".join(
    "localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(json.dumps(v))) for k, v in (("d2r_magicFinds", MF), ("d2r_owned", OWNED)))
MOVES = [["Fine Small Charm of Vita", "shared"], ["Stone Knot", "shared"], ["Stone Knot", "uni-armor"],
         ["Harlequin Crest", "no-such-locker"], ["Harlequin Crest", "uni-armor"], ["Nagelring", "uni-small"]]

BODY = r"""
(function(){
var W = window, MOVES = %s;
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); }
H.flush(60, 3);
function said(){ return String((document.getElementById('vault-status') || {}).textContent || ''); }
function amap(){ try { return JSON.parse(W.LSR.getItem('d2r_muleAssign') || '{}') || {}; } catch (e) { return 'UNREADABLE'; } }
OUT.census0 = W._vaultLockerItems('magic-rare');
OUT.m = [];
MOVES.forEach(function(p){
  var st = document.getElementById('vault-status'); if (st) st.textContent = '';
  var r; try { r = W.vaultAssign(p[0], p[1]); } catch (e) { r = 'THREW ' + String(e && e.message || e); }
  H.flush(60, 3);
  OUT.m.push({ name: p[0], to: p[1], ret: (r === undefined ? 'UNDEFINED' : r), said: said(), filed: amap()[p[0]] || null });
});
OUT.census1 = W._vaultLockerItems('magic-rare');
OUT.errors = H.errors.slice();
})();
""" % json.dumps(MOVES)


class AMoveThatDoesNotHappenSaysWhy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)
        cls.m = {(r["name"], r["to"]): r for r in cls.o["m"]}

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertNotIn("renderErr", self.o, self.o.get("renderErr"))
        self.assertEqual(self.o["errors"], [])

    def test_no_answer_is_undefined(self):
        bad = [(r["name"], r["to"]) for r in self.o["m"] if not isinstance(r["ret"], dict)]
        self.assertEqual(bad, [], "the move door returned nothing for: %r" % bad)

    def test_a_keeper_is_not_filed_where_nothing_draws_it_and_he_is_told_why(self):
        for key in (("Fine Small Charm of Vita", "shared"), ("Stone Knot", "shared"), ("Stone Knot", "uni-armor")):
            r = self.m[key]
            self.assertEqual((r["ret"].get("ok"), r["ret"].get("refused")), (False, "magic-rare-keeper"), "%r: %r" % (key, r))
            self.assertIsNone(r["filed"], "%r was filed beside its keeper record: %r" % (key, r))
            self.assertIn("Magic & Rare keeper", r["said"], "%r: the refusal was not said: %r" % (key, r["said"]))
            self.assertEqual(r["ret"].get("why"), r["said"].lstrip("\U0001f512 "), r)
        self.assertEqual(self.o["census1"], self.o["census0"], "a refused move changed what MAGIC & RARE holds")

    def test_a_locker_the_board_does_not_have_is_said(self):
        r = self.m[("Harlequin Crest", "no-such-locker")]
        self.assertEqual((r["ret"].get("ok"), r["ret"].get("refused")), (False, "no-mule"), r)
        self.assertIn("no-such-locker", r["said"], "the refusal was not said: %r" % r)

    def test_a_filing_answers_and_a_catalogue_item_in_magic_and_rare_still_files(self):
        r = self.m[("Harlequin Crest", "uni-armor")]
        self.assertEqual((r["ret"].get("ok"), r["ret"].get("mule"), r["filed"]), (True, "uni-armor", "uni-armor"), r)
        u = self.m[("Nagelring", "uni-small")]
        self.assertEqual((u["ret"].get("ok"), u["filed"]), (True, "uni-small"),
                         "a unique sitting in Magic & Rare was refused as a keeper (REG-2184 keeps its mule filing): %r" % u)


RED_PROOF = [
    {"why": "REG-2854 - a locker id the board does not have returns nothing and says nothing again",
     "file": "bible.html",
     "find": "      return { ok: false, refused: 'no-mule', why: _nmWhy };   /* REG-2854 said, never silent */\n",
     "replace": "      return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2854 - an owned keeper is 'filed' on the shared stash where nothing draws it (said as a move)",
     "file": "bible.html",
     "find": "    if (muleId !== 'magic-rare' && !_mrCat && typeof window._vaultInMagicRare === 'function' && window._vaultInMagicRare(name)){\n",
     "replace": "    if (false){\n",
     "matches": 1, "needs": "node"},
    # REG-3042 (#163) moved the catalogue test into _vaultInMagicRare, so the door's own `!_mrCat` can no longer decide (a name
    # _vaultInMagicRare holds is never a catalogue item): either alone is BLIND here. Both ask _vaultCatalogueItem - the one test.
    {"why": "REG-2854 - a unique sitting in Magic & Rare is refused as a keeper (REG-3042's one catalogue test forgets a unique)",
     "file": "bible.html",
     "find": "  function _vaultCatalogueItem(n){ return _vaIsGrailUni(n) || !!(typeof findSetPiece === 'function' && findSetPiece(n)) || _vaIsRW(n); }\n",
     "replace": "  function _vaultCatalogueItem(n){ return !!(typeof findSetPiece === 'function' && findSetPiece(n)) || _vaIsRW(n); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2854 - a filing returns nothing again",
     "file": "bible.html",
     "find": "    return { ok: true, mode: _vf.mode, mule: muleId };   /* REG-2854 a filing is an answer too */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
