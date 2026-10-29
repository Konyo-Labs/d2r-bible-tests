# -*- coding: utf-8 -*-
"""REG-3098 (#158) - THE REGISTER'S RECEIPT LOOK IS ONE REAL LOOK, NEVER TWO LOOKS' FIELDS SEWN TOGETHER.

Measured read-only on claude/int (836921abc) with his last vault sweep through the page in node: Storm Scarab, grounded by
the console on two sessions (conf 0.8 and 0.9, each with its own frame), was owned but refused filing - "only 1 qualifying
look in your stash ... (2 did not)" - while the console's gate and the board's own _vaultWitnessCheck, handed the same
looks, both count 2. Its first look was a legacy one with no frame and conf 0. tvVaultRegister built the owned receipt from
sessions[0] (that session and conf 0) beside another look's frame; _receiptStashWitness then put that chimera first and
de-duplicated the real 0.8 look of the same session and frame away. Of his 92 grounded rows, 4 start with a frameless look.
Now the receipt takes the first look that carries a frame - its own session, frame and conf together. Driven on the whole
page in node with a fixture of that shape. RED_PROOF below.
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

SEED = "localStorage.setItem('d2r_ownerClaim', '*');\nlocalStorage.setItem('d2r_vaultAutoIntake', 'on');\n"
BODY = r"""
(function(){
var W = window, A = 's_1790000000001_00001', B = 's_1790000000002_00002';
var looks = [{ session: A, frame: null, lane: 'stash', conf: 0.0 },                                   /* a legacy look: no frame */
             { session: A, frame: 'f_1790000000007.jpg', lane: 'stash', conf: 0.8, cell: 'stash:c5r6', witness: A + '#0' },
             { session: B, frame: 'f_1790000000014.jpg', lane: 'stash', conf: 0.9, witness: B + '#0' }];
OUT.check = (function(){ var c = W._vaultWitnessCheck({ lane: 'stash', sessions: looks }); return { ok: c.ok, n: (c.sessions || []).length }; })();
var r = W.tvVaultRegister('Storm Scarab', { lane: 'stash', sessions: looks, by: 'vault-sweep' });
OUT.r = r && { ok: !!r.ok, refused: r.refused || null, mule: r.mule || null, why: String(r.why || '') };
var pv = JSON.parse(localStorage.getItem('d2r_vaultProv') || '{}')['Storm Scarab'] || {};
OUT.mule = (JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}') || {})['Storm Scarab'] || null;
/* the receipt (who put it in owned) travels on the filing row as ownedBy; the filing row keeps every look */
var rc = (pv.kind === 'owned') ? pv : (pv.ownedBy || {});
OUT.receipt = { session: rc.sessionId || null, frame: rc.frameId || null, conf: (rc.conf == null ? null : rc.conf) };
OUT.filedLooks = (pv.looks || []).map(function(k){ return [k.id, k.frame, k.conf]; });
})();
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AReceiptLookIsOneRealLook(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=SEED, timeout=300)

    def test_premise_the_looks_are_two_sessions(self):
        self.assertEqual(self.o["check"], {"ok": True, "n": 2}, "PREMISE: the board's own check no longer counts 2")

    def test_it_files_on_the_two_sessions_it_carries(self):
        r = self.o["r"]
        self.assertNotEqual(r["refused"], "witness", "the filing saw fewer looks than the read carried: %r" % r)
        self.assertEqual(self.o["mule"], "magic-rare", "Storm Scarab was not filed: %r" % r)

    def test_the_receipt_is_one_look(self):
        rc = self.o["receipt"]
        self.assertEqual((rc["frame"], rc["conf"]), ("f_1790000000007.jpg", 0.8),
                         "the receipt sewed one look's frame to another's conf: %r" % rc)
        self.assertEqual(len(self.o["filedLooks"]), 2, "the filing kept %r" % self.o["filedLooks"])


RED_PROOF = [
    {"why": "REG-3098 - the receipt takes sessions[0] again (a frameless look's conf beside another look's frame)",
     "file": "bible.html",
     "find": "      var _l0 = _ls0.filter(function(x){ return x.frame || x.frameId; })[0] || _ls0[0] || {};\n",
     "replace": "      var _l0 = _ls0[0] || {};\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
