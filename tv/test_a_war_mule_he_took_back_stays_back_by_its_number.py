# -*- coding: utf-8 -*-
"""REG-2889 (the full-diff Grok second eye on the shipped v3834) - A WAR MULE HE TOOK BACK STAYS BACK, BY ITS NUMBER.

The eye's finding: "Take-back is keyed by the mule's current name, while the board decides the next mule by war number.
_vaultWarDecline pushes m.name; the make loop only skips 'WAR'+n." MEASURED (whole page in node, the real doors): the board
made WAR1 for Shako x3. He renamed it to a character (BARBIE, through vaultRenameMule) and deleted it (through
vaultDeleteMule, his confirm answered yes). The shared stash then held warDeclined ['BARBIE'], and the next paint minted a
new WAR1. The role and the number ride the mule's id (REG-2804); the take-back now rides the number too: 'WAR' + warN.

The eye's second finding on the same door was that a take-back is "recorded in memory and not written". MEASURED, it is
written: the shared stash's entry is an element of the roster the delete saves (saveR, one write), the stored roster held
warDeclined ['WAR1'], and a reload made nothing. That case stays here as a guard on the executed door, not on the source
order.

The delete door is async (it awaits his confirm). vault_page_node prints OUT once, synchronously, after the body. This law
holds that print and writes OUT itself once the door's promise settles: the same one line, written later. Never a browser.
RED_PROOF below.
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

# the door is async: hold the harness's one OUT line and write it when the door has settled
ASYNC = r"""
var __w = process.stdout.write.bind(process.stdout), __held = false;
process.stdout.write = function(s){ if (!__held && String(s).indexOf('__VAULT_PAGE_NODE_OUT__') >= 0) { __held = true; return true; } return __w(s); };
function done(){ process.stdout.write = __w; __w('\n__VAULT_PAGE_NODE_OUT__' + JSON.stringify(OUT) + '\n'); }
"""
LIB = ASYNC + r"""
var W = window, SH = %s;
function stored(){ return JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]'); }
function wars(){ return stored().filter(function(m){ return W._vaultWarRole(m) > 0; }).map(function(m){ return [m.id, m.name, W._vaultWarRole(m)]; }); }
function declined(){ var s = stored().filter(function(m){ return m.id === 'shared'; })[0]; return s ? (s.warDeclined || null) : 'no shared entry'; }
function paint(){ W.renderVault(); H.flush(60, 3); W.renderVault(); }
W._vaultAutoIntakeSet(false);
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); paint();
OUT.made = wars();
OUT.w1 = W._vaultWarName ? W._vaultWarName(1) : 'WAR1';   /* REG-2980 the board's name for war mule 1 */
window.uiConfirm = function(){ return Promise.resolve(true); };   /* his confirm: yes */
""" % json.dumps(SHAKO)
DELETE = LIB + r"""
(async function(){
  await W.vaultDeleteMule(OUT.made.length ? OUT.made[0][0] : null); paint();
  OUT.after = { wars: wars(), declined: declined() };
  OUT.raw = {}; H.RAW.forEach(function(v, k){ OUT.raw[k] = v; });
})().catch(function(e){ OUT.err = String(e && e.stack || e); }).then(done);
"""
RENAMED = LIB + r"""
window.prompt = function(){ return 'Barbie'; };                 /* his rename: a character's name */
(async function(){
  var id = OUT.made.length ? OUT.made[0][0] : null;
  W.vaultRenameMule(id); paint();
  OUT.renamed = wars();
  await W.vaultDeleteMule(id); paint();
  OUT.after = { wars: wars(), declined: declined() };
  OUT.raw = {}; H.RAW.forEach(function(v, k){ OUT.raw[k] = v; });
})().catch(function(e){ OUT.err = String(e && e.stack || e); }).then(done);
"""
RELOAD = r"""
var W = window;
W.renderVault(); H.flush(60, 3); W.renderVault();
OUT.wars = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return W._vaultWarRole(m) > 0; }).map(function(m){ return m.name; });
OUT.auto = W._vaultWarAuto || null;
"""


def _reload(o):
    raw = o.pop("raw", None) or {}
    carry = "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(v)) for k, v in raw.items())
    return VPN.run(RELOAD, prelude=carry, timeout=300)


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AWarMuleHeTookBackStaysBackByItsNumber(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d = VPN.run(DELETE, prelude=CLAIM, timeout=300)
        cls.dr = _reload(cls.d)
        cls.r = VPN.run(RENAMED, prelude=CLAIM, timeout=300)
        cls.rr = _reload(cls.r)

    def test_premise_the_board_made_war1(self):
        for o in (self.d, self.r):
            self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
            self.assertNotIn("err", o, o.get("err"))
            self.assertEqual([(w[1], w[2]) for w in o["made"]], [(o["w1"], 1)], "PREMISE: %r" % o["made"])

    def test_a_deleted_war1_is_written_with_the_roster_and_stays_gone_after_a_reload(self):
        a = self.d["after"]
        self.assertEqual((a["wars"], a["declined"]), ([], ["WAR1"]), a)
        self.assertEqual(self.dr["wars"], [], "a reload made the WAR1 he deleted again: %r" % self.dr)
        self.assertIn("took back", (self.dr["auto"] or {}).get("why") or "", self.dr["auto"])

    def test_a_war1_renamed_to_a_character_and_deleted_is_taken_back_by_its_number(self):
        r = self.r
        self.assertEqual([(w[1], w[2]) for w in r["renamed"]], [("BARBIE", 1)], "PREMISE: the rename did not land: %r" % r["renamed"])
        a = r["after"]
        self.assertEqual(a["declined"], ["WAR1"], "the take-back is keyed by the name he gave it: %r" % a)
        self.assertEqual(a["wars"], [], "the board minted a new WAR1 after he took the renamed one back: %r" % a["wars"])
        self.assertEqual(self.rr["wars"], [], "a reload minted a new WAR1: %r" % self.rr)


RED_PROOF = [
    {"why": "REG-2889 - the take-back is keyed by the mule's current name again (a renamed WAR1 comes back as a new WAR1)",
     "file": "bible.html",
     "find": "    var dl = (sh.warDeclined || []).slice(), key = 'WAR' + wn;",
     "replace": "    var dl = (sh.warDeclined || []).slice(), key = m.name;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2889 - the delete records no take-back (the board remakes the WAR1 he deleted)",
     "file": "bible.html",
     "find": "    try { _vaultWarDecline(m); } catch (eDl) {}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
