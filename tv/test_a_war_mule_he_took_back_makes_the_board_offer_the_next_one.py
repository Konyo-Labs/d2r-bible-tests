# -*- coding: utf-8 -*-
"""REG-2997 (his ruling 2026-10-29 ~02:30 IDT, Q2: when he declines war-A, the board offers the next one, war-B, when there is
overflow, with the same "make it in the game" task) - A WAR MULE HE TOOK BACK MAKES THE BOARD OFFER THE NEXT ONE.

MEASURED before (whole page in node, the real doors): the board made WAR-A for Shako x3; he deleted it (vaultDeleteMule, his
confirm answered yes). The next paint made nothing - _vaultWarAutoMule returned "you took back the WAR-A the board made" - and
the two copies past the war stash kept no cell for good. Now the number he took back is passed over and the next one is made
(war number 2, WAR-B), first in MOVE TASKS as a make task, with the copies' moves sent to it and a record that names the ones
he took back. A second take-back offers the third. With nothing past the war stash, a take-back still makes nothing.

The delete door is async (it awaits his confirm); vault_page_node prints OUT once, synchronously, after the body, so this law
holds that print and writes OUT itself once the doors have settled (REG-2889's way). Never a browser. RED_PROOF below.
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
SHAKO = "Harlequin Crest (Shako)"      # big war gear: the war cap keeps 1, the other copies need a WAR mule

ASYNC = r"""
var __w = process.stdout.write.bind(process.stdout), __held = false;
process.stdout.write = function(s){ if (!__held && String(s).indexOf('__VAULT_PAGE_NODE_OUT__') >= 0) { __held = true; return true; } return __w(s); };
function done(){ process.stdout.write = __w; __w('\n__VAULT_PAGE_NODE_OUT__' + JSON.stringify(OUT) + '\n'); }
"""
BASE = r"""
var W = window, SH = %s;
function stored(){ return JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]'); }
function wars(){ return stored().filter(function(m){ return W._vaultWarRole(m) > 0; }); }
function paint(){ W.renderVault(); H.flush(60, 3); W.renderVault(); }
function makeRows(){ var l = (document.getElementById('vault-move-list') || {}).innerHTML || '';
  return (l.match(/<li class="vtk-line vtk-make"[\s\S]*?<\/li>/g) || []).map(function(x){ return x.replace(/<[^>]+>/g, ''); }); }
function holders(){ var o = []; for (var ci = 0; ci < copyCount(SH); ci++) { var t = (W._vaultMoveEnsure(SH, ci) || {}).task; o.push(t && t.to ? (t.to.holder || null) : null); } return o; }
function look(){ return { wars: wars().map(function(m){ return [m.name, W._vaultWarRole(m), (m.auto || {}).why || null]; }), make: makeRows(), holders: holders() }; }
OUT.names = [1, 2, 3].map(function(n){ return W._vaultWarName(n); });
window.uiConfirm = function(){ return Promise.resolve(true); };   /* his confirm: yes */
W._vaultAutoIntakeSet(false);
""" % json.dumps(SHAKO)
TWICE = ASYNC + BASE + r"""
(async function(){
  [SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); paint();
  OUT.first = look();
  await W.vaultDeleteMule(wars()[0].id); paint();
  OUT.second = look();
  await W.vaultDeleteMule(wars()[0].id); paint();
  OUT.third = look();
})().catch(function(e){ OUT.err = String(e && e.stack || e); }).then(done);
"""
QUIET = BASE + r"""
paint();
OUT.copies = copyCount(SH); OUT.after = look(); OUT.full = (W._vaultWarFull || []).length;
"""


def _quiet_prelude():
    """he took war mule 1 back, and he holds ONE Shako: the war stash keeps it, nothing is past it"""
    r = VPN.run("OUT.r = JSON.parse(window.LSR.getItem('d2r_muleRoster') || 'null') || "
                "(window._vaultRosterNow && window._vaultRosterNow());", prelude=CLAIM, timeout=300).get("r")
    if not isinstance(r, list) or not r:
        raise AssertionError("PREMISE: the page has no default roster: %r" % (r,))
    for m in r:
        if m.get("id") == "shared":
            m["warDeclined"] = ["WAR1"]
    return (CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n" % json.dumps(json.dumps(r))
            + "localStorage.setItem('d2r_owned', %s);\nlocalStorage.setItem('d2r_copies', %s);\n"
            % (json.dumps(json.dumps([SHAKO])), json.dumps(json.dumps({SHAKO: 1}))))


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AWarMuleHeTookBackMakesTheBoardOfferTheNextOne(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.t = VPN.run(TWICE, prelude=CLAIM, timeout=300)
        cls.q = VPN.run(QUIET, prelude=_quiet_prelude(), timeout=300)

    def _case(self, o):
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertNotIn("err", o, o.get("err"))

    def test_premise_the_board_made_war_mule_1_for_the_overflow(self):
        o = self.t
        self._case(o)
        self.assertEqual([w[:2] for w in o["first"]["wars"]], [[o["names"][0], 1]], "PREMISE: %r" % o["first"])

    def test_he_takes_war_mule_1_back_and_the_board_offers_war_mule_2(self):
        o, a, b = self.t, self.t["first"], self.t["second"]
        self._case(o)
        self.assertEqual([w[:2] for w in b["wars"]], [[o["names"][1], 2]], "the board did not offer the next war mule: %r" % b)
        self.assertIn("you took back %s, so this is the next one" % o["names"][0], b["wars"][0][2] or "", b["wars"])
        self.assertTrue([t for t in b["make"] if ("Create mule %s in the game" % o["names"][1]) in t],
                        "he is not tasked to make it in the game: %r" % b["make"])
        na = [h for h in a["holders"] if h == o["names"][0]]
        self.assertTrue(na, "PREMISE: no copy went to war mule 1: %r" % a["holders"])
        self.assertEqual([h for h in b["holders"] if h and h.upper().startswith("WAR")], [o["names"][1]] * len(na),
                         "the copies past the war stash do not go to the new war mule: %r -> %r" % (a["holders"], b["holders"]))

    def test_a_second_take_back_offers_the_third(self):
        o, c = self.t, self.t["third"]
        self._case(o)
        self.assertEqual([w[:2] for w in c["wars"]], [[o["names"][2], 3]], "the board did not offer the third war mule: %r" % c)
        self.assertIn("you took back %s, %s, so this is the next one" % (o["names"][0], o["names"][1]), c["wars"][0][2] or "", c["wars"])

    def test_with_nothing_past_the_war_stash_a_take_back_makes_nothing(self):
        q = self.q
        self._case(q)
        self.assertEqual(q["copies"], 1, "PREMISE: the law could not hold Shako at one copy: %r" % q)
        self.assertEqual(q["full"], 0, "PREMISE: there is still overflow: %r" % q)
        self.assertEqual(q["after"]["wars"], [], "the board made a war mule with nothing past the war stash: %r" % q["after"])


RED_PROOF = [
    {"why": "REG-2997 - a take-back ends the make again (war mule 2 is never offered)",
     "file": "bible.html",
     "find": "        if (_dl) _took.push(name);\n",
     "replace": "        if (_dl) { fresh(); return { made: made, why: 'you took back the ' + name + ' the board made' }; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2997 - the board makes the war mule he took back again",
     "file": "bible.html",
     "find": "        var _dl = (sh.warDeclined || []).indexOf('WAR' + n) >= 0;",
     "replace": "        var _dl = false;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2997 - the record does not say which ones he took back",
     "file": "bible.html",
     "find": "                        + (_took.length ? '; you took back ' + _took.join(', ') + ', so this is the next one' : '') } };",
     "replace": "                        } };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2997 - only the first take-back is passed over (a second one ends the make)",
     "file": "bible.html",
     "find": "      for (var _wn = 0; _wn < 52; _wn++) {",
     "replace": "      for (var _wn = 0; _wn < 1; _wn++) {",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
