# -*- coding: utf-8 -*-
"""REG-2996 (his ruling 2026-10-29 ~02:30 IDT, Q1: overflow names go "per locker, letters only (armor-A, weapon-A), one mule per
category") - A LOCKER'S NEXT MULE IS NAMED BY A NAME THE GAME ACCEPTS.

A locker's Mule 2+ is a character he makes in the game (REG-2875). MOVE TASKS asked him to "Create mule UNI-ARMOR #2 in the
game", but a D2R name is 2-15 letters with at most one '-' or '_' and no digit (agent-guide's measurement, REG-2980). So he
could never create that name. Now one helper names a locker's Mule k (k >= 2) by its word and a letter: UNI-ARMOR's Mule 2 is
ARMOR-A and its Mule 3 is ARMOR-B; UNI-WEAPONS' Mule 2 is WEAPON-A. A core locker's word rides its id, so renaming the locker
never renames a character he has already made. A mule he added uses the letters of its own name.
Every surface that names the page spells it the same way, "Mule 2 · ARMOR-A": the make task, the move row, FIND and its
target, and the mule window's header. This pins the RULE: a legal name derived from the locker and k, mapped back to k, and
distinct across lockers. His two examples are pinned as his words. Whole page in node, never a browser. RED_PROOF below.
"""
import json
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
LEGAL = re.compile(r"^[A-Za-z]+(?:[-_][A-Za-z]+)?$")     # letters, at most one '-' or '_', no digit


def _legal(name):
    return bool(LEGAL.match(name or "")) and 2 <= len(name) <= 15


def _letters_n(t):
    n = 0
    for ch in t:
        n = n * 26 + (ord(ch) - 64)
    return n


RULE = r"""
var W = window, ros = W._vaultRosterNow() || [];
OUT.ids = ros.map(function(m){ return m.id; });
OUT.names = {}; ros.forEach(function(m){ var a = []; for (var k = 1; k <= 30; k++) a.push(W._vaultLockerMuleName(m, k)); OUT.names[m.id] = a; });
OUT.renamed = W._vaultLockerMuleName({ id: 'uni-armor', name: 'BARBIE' }, 2);
OUT.added = W._vaultLockerMuleName({ id: 'm1abcdefg', name: 'My Stuff 2', added: true }, 2);
OUT.say = [W._vaultLockerMuleSay({ id: 'uni-armor', name: 'UNI-ARMOR' }, 1), W._vaultLockerMuleSay({ id: 'uni-armor', name: 'UNI-ARMOR' }, 2)];
"""
PAGE = r"""
var W = window;
function paint(){ W.renderVault(); H.flush(60, 3); }
function list(){ return (document.getElementById('vault-move-list') || {}).innerHTML || ''; }
function row(n){ W.vaultFind(n.toLowerCase()); H.flush(400, 3);
  var h = (document.getElementById('vault-find-results') || {}).innerHTML || '';
  var r = (h.match(/<div class="vfr-row"[\s\S]*?<\/div>(?=<div class="vfr-row"|$)/) || [''])[0];
  return (r.match(/<span class="vfr-cell[^"]*">([^<]*)</) || [])[1] || ''; }
W._vaultAutoIntakeSet(false);
var arm = [];
ITEMS.forEach(function(it){ var n = it.name || it.n || it[0]; if (!n || arm.length >= 45) return; var p = null; try { p = W.vaultPropose(n); } catch (e) {}
  if (p && p.ok && p.id === 'uni-armor') arm.push(n); });
arm.forEach(function(n){ W.vaultHandAdd(n); });
paint();
var ua = (W._vaultRosterNow() || []).filter(function(m){ return m.id === 'uni-armor'; })[0] || null;
OUT.name2 = W._vaultLockerMuleName(ua, 2); OUT.say2 = W._vaultLockerMuleSay(ua, 2);
OUT.make = (list().match(/<li class="vtk-line vtk-make"[^>]*data-mule="uni-armor"[^>]*data-page="2"[\s\S]*?<\/li>/g) || [])
  .map(function(x){ return x.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); });
OUT.rows = (list().match(/<span class="vtk-to">[^<]*/g) || []).map(function(s){ return s.replace('<span class="vtk-to">', ''); })
  .filter(function(t){ return /^UNI-ARMOR · Mule 2\b/.test(t); });
var where = {}; arm.forEach(function(n){ var w = W._vaultWhereIs(n); where[n] = w ? String(w.cell || '') : ''; });
OUT.onTwo = arm.filter(function(n){ return /^Mule 2\b/.test(where[n]); })[0] || null;
OUT.where = OUT.onTwo ? where[OUT.onTwo] : null;
OUT.find = OUT.onTwo ? row(OUT.onTwo) : null;
OUT.kind = OUT.onTwo ? (W._vaultWhereIs(OUT.onTwo) || {}).kind : null;
/* his assign door files every one on UNI-ARMOR: the where-is answer of a FILED copy */
arm.forEach(function(n){ W.vaultAssign(n, 'uni-armor'); }); paint();
var whereF = {}; arm.forEach(function(n){ var w = W._vaultWhereIs(n); whereF[n] = w ? [w.kind, String(w.cell || '')] : null; });
OUT.filed = arm.map(function(n){ return whereF[n]; }).filter(function(x){ return x && x[0] === 'filed' && /^Mule 2\b/.test(x[1]); })[0] || null;
W._muleOpenAt('uni-armor', 1); H.flush(60, 3);
OUT.header = (((document.getElementById('vault-detail') || {}).innerHTML || '').match(/<span class="vd-name">([^<]*)<\/span>/) || [])[1] || null;
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ALockersNextMuleIsNamedByANameTheGameAccepts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rule = VPN.run(RULE, prelude=CLAIM, timeout=300)
        cls.page = VPN.run(PAGE, prelude=CLAIM, timeout=600)

    def test_every_lockers_mule_k_has_a_legal_name_of_its_own_that_maps_back_to_k(self):
        r = self.rule
        self.assertEqual(r["__boot"]["errors"], [], r["__boot"])
        self.assertIn("uni-armor", r["ids"], "PREMISE: no UNI-ARMOR locker: %r" % r["ids"])
        seen = {}
        for mid, names in r["names"].items():
            if mid == "shared":
                continue
            self.assertIsNone(names[0], "%s's Mule 1 is its own character - no name is derived: %r" % (mid, names[0]))
            for k, nm in enumerate(names[1:], start=2):
                self.assertTrue(_legal(nm), "%s's Mule %d is named %r, a name the game refuses" % (mid, k, nm))
                self.assertEqual(_letters_n(nm.split("-")[1]), k - 1, "%r does not map back to Mule %d" % (nm, k))
                self.assertNotIn(nm, seen, "%s's Mule %d and %s share the name %r" % (mid, k, seen.get(nm), nm))
                seen[nm] = (mid, k)

    def test_his_examples_and_a_renamed_locker(self):
        r = self.rule
        self.assertEqual((r["names"]["uni-armor"][1], r["names"]["uni-weap"][1]), ("ARMOR-A", "WEAPON-A"), "his words: armor-A, weapon-A")
        self.assertEqual(r["names"]["uni-armor"][2], "ARMOR-B")
        self.assertEqual(r["renamed"], "ARMOR-A", "renaming the locker renamed the character he made for its Mule 2: %r" % r["renamed"])
        self.assertEqual(r["added"], "MYSTUFF-A", "a mule he added is not named by its own letters: %r" % r["added"])
        self.assertEqual(r["say"], ["Mule 1", "Mule 2 · ARMOR-A"], r["say"])

    def test_every_surface_spells_mule_2_the_same_way(self):
        p = self.page
        self.assertEqual(p["__boot"]["errors"], [], p["__boot"])
        nm, say = p["name2"], p["say2"]
        self.assertTrue(_legal(nm), "PREMISE: %r" % nm)
        self.assertEqual(len(p["make"]), 1, "MOVE TASKS does not ask once for UNI-ARMOR's Mule 2: %r" % p["make"])
        self.assertIn("Create mule %s in the game" % nm, p["make"][0], p["make"])
        self.assertNotRegex(p["make"][0], r"#\d", "the make task still asks for a '#' name: %r" % p["make"])
        self.assertTrue(p["rows"], "PREMISE: no move row goes to UNI-ARMOR's Mule 2")
        for t in p["rows"]:
            self.assertRegex(t, r"^UNI-ARMOR · " + re.escape(say) + r" \(\d+,\d+\)$", "the move row does not name the character: %r" % t)
        self.assertTrue(p["onTwo"], "PREMISE: no hand add sits on UNI-ARMOR's Mule 2")
        self.assertTrue(p["where"].startswith(say + " · "), "the where-is cell of a hand add (%s) does not name the character: %r" % (p["kind"], p["where"]))
        self.assertTrue(p["filed"], "PREMISE: no filed copy sits on UNI-ARMOR's Mule 2")
        self.assertTrue(p["filed"][1].startswith(say + " · "), "the where-is cell of a filed copy does not name the character: %r" % p["filed"])
        self.assertTrue((p["find"] or "").startswith(" · " + say + " · "), "FIND's cell does not name the character: %r" % p["find"])
        self.assertEqual(p["header"], "UNI-ARMOR · %s" % nm, "the mule window's header for Mule 2: %r" % p["header"])


RED_PROOF = [
    {"why": "REG-2996 - a locker's Mule k is named '<locker> #k' again, a name the game refuses",
     "file": "bible.html",
     "find": "    return w + '-' + _vaultLetters(k - 1);\n  }\n",
     "replace": "    return String(m.name) + ' #' + k;\n  }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2996 - a core locker's word follows its name, so his rename renames a character he made",
     "file": "bible.html",
     "find": "    var w = WORD[m.id] || String(m.name || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 12);",
     "replace": "    var w = String(m.name || '').toUpperCase().replace(/[^A-Z]/g, '').slice(0, 12);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2996 - the make task asks for 'UNI-ARMOR #2' again",
     "file": "bible.html",
     "find": "'<span class=\"vtk-say\">Create mule <b>' + esc(r.char) + '</b> in the game",
     "replace": "'<span class=\"vtk-say\">Create mule <b>' + esc(r.name + ' #' + r.mule) + '</b> in the game",
     "matches": 1, "needs": "node"},
    {"why": "REG-2996 - the move row names Mule 2 without its character",
     "file": "bible.html",
     "find": "return h + ' · ' + _vaultLockerMuleSay(_pm, _ca.page + 1) + ' ('",
     "replace": "return h + ' · Mule ' + (_ca.page + 1) + ' ('",
     "matches": 1, "needs": "node"},
    {"why": "REG-2996 - the where-is cell of a hand add (the would answer) names Mule 2 without its character",
     "file": "bible.html",
     "find": "            var tagW = (loadW.mules.length > 1 ? _vaultLockerMuleSay(wm, pi + 1) + ' · ' : '');",
     "replace": "            var tagW = (loadW.mules.length > 1 ? 'Mule ' + (pi + 1) + ' · ' : '');",
     "matches": 1, "needs": "node"},
    {"why": "REG-2996 - the where-is cell of a filed copy names Mule 2 without its character",
     "file": "bible.html",
     "find": "            var tag = (load.mules.length > 1 ? _vaultLockerMuleSay(m, pi + 1) + ' · ' : '');",
     "replace": "            var tag = (load.mules.length > 1 ? 'Mule ' + (pi + 1) + ' · ' : '');",
     "matches": 1, "needs": "node"},
    {"why": "REG-2996 - FIND's target cell names Mule 2 without its character",
     "file": "bible.html",
     "find": "      var mk = (typeof _vaultLockerMuleSay === 'function') ? _vaultLockerMuleSay(mule, ca.page + 1) : 'Mule ' + (ca.page + 1);",
     "replace": "      var mk = 'Mule ' + (ca.page + 1);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2996 - the mule window's header reads 'UNI-ARMOR #2' again",
     "file": "bible.html",
     "find": "    var _muleLabel = _muleTotalPages > 1 ? (_mulePage >= 1 ? ' · ' + _vaultLockerMuleName(m, _mulePage + 1) : ' #1') : '';",
     "replace": "    var _muleLabel = _muleTotalPages > 1 ? (' #' + (_mulePage + 1)) : '';",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
