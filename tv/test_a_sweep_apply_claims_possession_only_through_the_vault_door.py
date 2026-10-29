# -*- coding: utf-8 -*-
"""REG-3086 (#158, GrokBot #230 10-21 "0 of 39 real reads auto-muled") - A SWEEP APPLY CLAIMS POSSESSION ONLY THROUGH THE
VAULT'S ONE DOOR.

Measured read-only on claude/int (836921abc) with his own last sweep (vault_last_result.json, 92 grounded rows) built into
the payload exactly as control_app.vault_apply builds it and run through the page's window.vaultAccumApply in node:
  * AUTO INTAKE off (the default): tvVaultRegister refused all 89 reads 'auto-intake-off' - and 67 names were OWNED anyway,
    none filed: the Unsorted pile GrokBot counted, "0 auto-muled";
  * AUTO INTAKE on: 72 of 92 filed, but a Full Rejuvenation Potion and two materials the door refused 'not-an-item' were
    owned all the same, and every first register answered 'already'.
The second writer: vaultAccumApply -> chronicleApply called toggleOwned(n) for every row BEFORE the vault door, and for a
name the grail does not hold toggleOwned's physical arm writes d2r_owned - no AUTO INTAKE, no two-session rule, no
not-an-item refusal, no container (v2388 already says a chronicle sighting is not a possession claim). Now chronicleApply
asks toggleOwned for the grail tick only (grailOnly) for a READ's row, toggleOwned's physical arm refuses that caller, and
possession is tvVaultRegister's alone. HIS HAND IS NEVER STOPPED BY THIS: his item-card tick (toggleOwned, no grailOnly) owns the
same name the apply was refused, and a row that is his hand (source 'hand') keeps toggleOwned's whole answer even through
chronicleApply. Grail ticks are unchanged. After the fix, on his sweep: off ->
0 owned; on -> 72 filed and the refused three are not owned.

Driven on the whole page in node with a payload of the console's own shape (fixture names, sessions and frames - never his
data). RED_PROOF below.
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


def _row(name, sessions):
    """one grounded row as vault_retro.apply_payload ships it: its looks, each its own session and frame"""
    ws = [{"session": "s_17900000%05d_%05d" % (i, i), "frame": "f_17900000%05d.jpg" % (i * 7), "lane": "stash", "conf": 0.9,
           "cell": "stash:c%dr1" % i, "witness": "s_17900000%05d_%05d#0" % (i, i)} for i in sessions]
    return {"name": name, "lane": "stash", "kind": "item", "count": None, "conf": 0.9, "witnesses": ws,
            "witnessCount": len(ws), "lastSeenTs": None,
            "gate": {"pass": len(sessions) >= 2, "why": "fixture", "looks": len(sessions), "looksSeen": len(sessions),
                     "wilson": None, "floor": 0.55, "minLooks": 2}}


ITEMS = [_row("Shadow Amulet", [1, 2]),              # a magic amulet: MAGIC & RARE, never a grail name
         _row("Full Rejuvenation Potion", [3, 4]),   # a count (REG-2899): the door refuses it
         _row("Gheed's Fortune", [5, 6]),            # a grail unique: its tick is the chronicle's
         _row("Bone Beads", [7])]                    # a rare amulet on ONE session: held, never owned
PAYLOAD = {"ok": True, "source": "vault-accumulator", "mode": "merge-max", "items": ITEMS, "owned": ITEMS,
           "unsure": [], "throwOut": [], "suggestions": [], "held": [], "glimpsed": [], "reconciled": [], "overRead": []}

BODY = r"""
(function(){
var W = window, P = __P__, LOG = [];
var real = W.tvVaultRegister;
W.tvVaultRegister = function(nm){ var r = real.apply(this, arguments);
  LOG.push({ name: nm, mode: r && r.mode || null, refused: r && r.refused || null }); return r; };
var res = W.vaultAccumApply(P);
H.flush(60, 3);
function J(k){ try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return 'UNREADABLE'; } }
OUT.owned = Array.from(owned).sort();
OUT.assign = J('d2r_muleAssign') || {};
OUT.found = Object.keys(J('d2r_foundLog') || {});
OUT.log = LOG;
OUT.ok = !!(res && res.ok);
/* his card tick is untouched: the SAME name the apply did not own, ticked by his hand, is owned */
OUT.beforeHand = owned.has('Shadow Amulet');
W.toggleOwned('Shadow Amulet');
OUT.handTick = owned.has('Shadow Amulet');
/* and a row that IS his hand keeps toggleOwned's whole answer through chronicleApply */
W.chronicleApply({ wouldAdd: { uniques: [{ name: 'Monarch', source: 'hand' }], sets: [] } });
OUT.handRow = owned.has('Monarch');
/* and a grail-only caller is refused on the physical arm */
W.toggleOwned('Archon Plate', { source: 'fixture', grailOnly: true });
OUT.grailOnly = owned.has('Archon Plate');
})();
""".replace("__P__", json.dumps(PAYLOAD))


def _seed(auto):
    return ("localStorage.setItem('d2r_ownerClaim', '*');\n"
            "localStorage.setItem('d2r_vaultAutoIntake', %s);\n" % json.dumps(auto))


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ASweepApplyClaimsPossessionOnlyThroughTheVaultDoor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.off = VPN.run(BODY, prelude=_seed("off"), timeout=300)
        cls.on = VPN.run(BODY, prelude=_seed("on"), timeout=300)

    def test_auto_intake_off_owns_nothing_from_the_sweep(self):
        o = self.off
        self.assertTrue(o["ok"], "PREMISE: the apply did not run")
        self.assertTrue(o["log"], "PREMISE: the vault door was never asked")
        self.assertEqual({e["refused"] for e in o["log"]}, {"auto-intake-off"}, o["log"])
        self.assertEqual(o["owned"], [], "AUTO INTAKE is off and the sweep apply still owned: %r" % o["owned"])
        self.assertIn("Gheed's Fortune", o["found"], "the grail tick is the chronicle's and must still land")

    def test_auto_intake_on_files_through_the_door(self):
        o = self.on
        self.assertIn("Shadow Amulet", o["owned"])
        self.assertEqual(o["assign"].get("Shadow Amulet"), "magic-rare", "the magic amulet was not filed: %r" % o["assign"])
        first = [e for e in o["log"] if e["name"] == "Shadow Amulet"][0]
        self.assertEqual(first["mode"], "new", "a second writer owned it before the vault door was asked: %r" % first)

    def test_a_refused_read_is_never_owned(self):
        o = self.on
        rej = [e for e in o["log"] if e["name"] == "Full Rejuvenation Potion"]
        self.assertTrue(rej and rej[0]["refused"] == "not-an-item", "PREMISE: the door no longer refuses a rejuv: %r" % rej)
        self.assertNotIn("Full Rejuvenation Potion", o["owned"], "the door refused it and the apply owned it anyway")

    def test_a_one_session_read_is_held_not_owned(self):
        self.assertNotIn("Bone Beads", self.on["owned"], "a one-session read was owned through the sweep apply")

    def test_his_hand_owns_what_the_read_could_not(self):
        o = self.off
        self.assertFalse(o["beforeHand"], "PREMISE: the read already owned it")
        self.assertTrue(o["handTick"], "AUTO INTAKE off stopped HIS hand-tick, not only the reader")
        for x in (self.on, self.off):
            self.assertTrue(x["handRow"], "a row that is his hand no longer owns through chronicleApply")
            self.assertFalse(x["grailOnly"], "a grail-only caller wrote possession")


RED_PROOF = [
    {"why": "REG-3086 - chronicleApply's toggle claims possession again (AUTO INTAKE off still owns the sweep)",
     "file": "bible.html",
     "find": "                                  loc: (row && row.loc) || null, conf: _s0.conf, grailOnly: !_byHand });",
     "replace": "                                  loc: (row && row.loc) || null, conf: _s0.conf });",
     "matches": 1, "needs": "node"},
    {"why": "REG-3086 - toggleOwned's physical arm takes a grail-only caller again",
     "file": "bible.html",
     "find": "    if (prov && prov.grailOnly) return false;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3086 - his hand's row through chronicleApply is made grail-only too (his hand stopped with the reader)",
     "file": "bible.html",
     "find": "                                  loc: (row && row.loc) || null, conf: _s0.conf, grailOnly: !_byHand });",
     "replace": "                                  loc: (row && row.loc) || null, conf: _s0.conf, grailOnly: true });",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
