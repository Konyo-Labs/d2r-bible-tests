# -*- coding: utf-8 -*-
"""REG-3099 (#148) - HIS HAND PLACEMENT SURVIVES THE RELOAD, WHICHEVER STEP SAVES THE MULE MAP FIRST.

tests/v2200:52 ("a migration overwrote his manual placement of 'Key of Hate'") was red on both attempts on main 014d4fc3d
and flaky elsewhere. CI's trace of the red attempt: after the reload, "[vault] seed cleanse: removed 1 ... spared 3" -
and d2r_muleAssign['Key of Hate'] was gone. Replayed on the whole page in node, step by step:
  * the vault paint's prune tests "still owned" against `pool`, and `pool` is the DOCK's list - it drops the
    account-shared-stash names (runes, keys, essences ...). 'Key of Hate' is one, so its '__keep' row was deleted from the
    map IN MEMORY at every paint, while d2r_muleAssign still held it;
  * the next whole-map save wrote memory over the store. On that load it was the seed cleanse's own removal (it took
    the unfiled 'The Stone of Jordan', correctly, through vaultRemove -> saveA); it could as well be any filing.
Whether a save followed the paint on the reloaded page depended on which page ran the deferred cleanse first - hence
"sometimes". His rule: his hand always wins; no reader, migration or prune undoes a manual placement.
FIX: the prune reads the whole owned pool (`poolAll`). This law drives it deterministically - boot, seed, reload, paint,
then the cleanse's save - so it reds every time on the defect, never sometimes. And the prune still does its job: a
filing whose item left owned, unwitnessed, still goes. RED_PROOF below.
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

OWNER = "localStorage.setItem('d2r_ownerClaim','*');\n"   # a file:// page under automation is his world (bare keys)
SEED = r"""
var own = ['Key of Hate', 'Annihilus', 'Nagelring', 'Manald Heal', 'The Stone of Jordan'];
var asg = {'Key of Hate': '__keep', 'Annihilus': '__keep', 'Nagelring': '__keep', 'Manald Heal': '__keep',
           'Harlequin Crest': 'uni-armor'};
LSR.setItem('d2r_owned', JSON.stringify(own));
LSR.setItem('d2r_muleAssign', JSON.stringify(asg));
OUT.sharedKey = (typeof isSharedStash === 'function') ? isSharedStash('Key of Hate') : null;
var d = {}; for (var i = 0; i < localStorage.length; i++){ var k = localStorage.key(i); d[k] = localStorage.getItem(k); }
OUT.dump = d;
"""
RELOAD = r"""
H.flush(120000, 8);
try { window.renderVault(); } catch (e) { OUT.renderErr = String(e); }      /* the paint and its prune */
var names = Object.keys(_GRAIL_SEED).concat(Object.keys(typeof _UNI_EXTRA !== 'undefined' ? _UNI_EXTRA : {}));
try { OUT.sc = window._seedCleanse({ names: names, seed: _GRAIL_SEED, mainLedger: 'absent - no console on this page' }); }
catch (e) { OUT.sc = 'ERR ' + e; }                                            /* the deferred chain's own save */
OUT.assign = JSON.parse(LSR.getItem('d2r_muleAssign') || '{}');
OUT.owned = JSON.parse(LSR.getItem('d2r_owned') || '[]');
"""


@unittest.skipIf(VPN.NODE is None, "node is absent - this law is UNMEASURED here, not passing")
class HisPlacementSurvivesTheReload(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        r1 = VPN.run(SEED, prelude=OWNER, timeout=600)
        cls.seed = r1
        pre = OWNER + "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(v)) for k, v in r1["dump"].items())
        cls.o = VPN.run(RELOAD, prelude=pre, timeout=600)

    def test_premise_the_reload_ran_the_paint_and_a_whole_map_save(self):
        self.assertIs(self.seed["sharedKey"], True, "PREMISE: 'Key of Hate' is no longer a shared-stash name")
        self.assertIsNone(self.o.get("renderErr"), self.o.get("renderErr"))
        sc = self.o["sc"]
        self.assertTrue(isinstance(sc, dict) and sc.get("ran"), "PREMISE: the cleanse did not run: %r" % (sc,))
        self.assertIn("The Stone of Jordan", sc["receipt"]["removed"], "PREMISE: no whole-map save followed the paint")
        self.assertNotIn("The Stone of Jordan", self.o["owned"])

    def test_his_keep_placements_survive_whichever_step_saves(self):
        for n in ("Key of Hate", "Annihilus", "Nagelring", "Manald Heal"):
            self.assertEqual(self.o["assign"].get(n), "__keep", "the reload undid his placement of %r" % n)

    def test_the_prune_still_drops_a_filing_whose_item_left_owned(self):
        self.assertNotIn("Harlequin Crest", self.o["assign"], "the prune no longer drops an unwitnessed filing of an item "
                                                              "he no longer owns")


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {"why": "REG-3099 - the prune tests the dock's pool again, so a shared-stash item's placement is dropped at the next save",
     "file": "bible.html",
     "find": "      if (poolAll.indexOf(n) >= 0) return;\n",
     "replace": "      if (pool.indexOf(n) >= 0) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3099 - the prune drops a filing whose item is still owned and nothing else",
     "file": "bible.html",
     "find": "      if (poolAll.indexOf(n) >= 0) return;\n",
     "replace": "      if (false) return;\n",
     "matches": 1, "needs": "node"},
]
