# -*- coding: utf-8 -*-
"""v3849 B9 (vault batch 2026-10-31) - SHARED STASH DOES NOT SWALLOW ORDINARY UNIQUES.

Measured before (the whole page in node): a hand-added unique the trade data calls TRASH (Bane Ash, Bladebuckle,
Iceblink) was sent to the shared stash by the L1 "a hand add is never unsorted" line - 133 of the batch landed there,
unpacked, with the gauge UNKNOWN. A hand add is still never unsorted, but it is filed by its kind: the uni weapon,
armor or small mule. War gear (Andariel's Visage, merc) stays shared; an item that is not hand-added keeps the
throw-out advice.
"""
import os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

BODY = r"""
var hand = ['Bane Ash', 'Bladebuckle', 'Iceblink', "Andariel's Visage"];
var r = {};
hand.concat(['Nokozan Relic']).forEach(function(n){ var h = window._vaultSeamHome(n); r[n] = [h && h.loc, h && h.mule, window._vaultHandTyped(n)]; });
r._plain = suggestMule('Bane Ash');
OUT.r = r;
"""


PRELUDE = ("localStorage.setItem('d2r_ownerClaim','*');"
           "var _hp={}; ['Bane Ash','Bladebuckle','Iceblink',\"Andariel's Visage\"].forEach(function(n){"
           "_hp[n]={source:'hand',where:'Add an item',by:'the Vault'};});"
           "localStorage.setItem('d2r_vaultProv', JSON.stringify(_hp));")


class TrashUniqueByKind(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, prelude=PRELUDE, timeout=300)["r"]

    def test_the_fixture_is_hand_typed(self):
        self.assertTrue(self.r["Bane Ash"][2])

    def test_trash_uniques_file_on_their_kind_mule(self):
        self.assertEqual(self.r["Bane Ash"][:2], ["filed", "uni-weap"])
        self.assertEqual(self.r["Bladebuckle"][:2], ["filed", "uni-armor"])
        self.assertEqual(self.r["Iceblink"][:2], ["filed", "uni-armor"])

    def test_war_gear_stays_shared(self):
        self.assertEqual(self.r["Andariel's Visage"][0], "shared")

    def test_the_advice_is_unchanged(self):
        self.assertEqual(self.r["_plain"]["id"], "__throwout")


RED_PROOF = [
    {"why": "v3849 B9 - a hand-added trash unique falls back to the shared stash",
     "file": "bible.html",
     "find": "if (sg.id === '__throwout' && /trade value TRASH/.test(String(sg.why || ''))) {",
     "replace": "if (false) {",
     "matches": 1},
    {"why": "v3849 B9 - the router cannot be asked past the trash line",
     "file": "bible.html",
     "find": "    if (_tv === 'trash' && !(opts && opts.ignoreTrash)) {",
     "replace": "    if (_tv === 'trash') {",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
