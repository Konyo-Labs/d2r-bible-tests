# -*- coding: utf-8 -*-
"""v3849 (Elad 2026-10-31 12:14-12:16, the ALT shadow) - TWO ROUTING RULINGS.

1. Dream and Faith go to the RUNEWORDS mule, not WAR / the shared stash (they were on WAR_GEAR).
2. The ALT's UNI-SMALL held Protector's Stone and Guardian's Thunder (his "protector / colossal jewels"; the exact names
   are from the ALT roster cache). The six Colossal Ancient jewels are war stash gear: the shared stash, never UNI-SMALL.
Enigma and Grief stay war gear; a plain unique jewel such as Rainbow Facet keeps its own (high trade value) rule.
Measured on the whole page in node (tv/vault_page_node.py): suggestMule and the dock seam.
"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

NAMES = ["Dream", "Faith", "Enigma", "Grief", "Protector's Stone", "Guardian's Thunder", "Defender's Bile",
         "Protector's Frost", "Guardian's Light", "Defender's Fire", "Rainbow Facet"]
BODY = ("var r={}; %s.forEach(function(n){ var s=suggestMule(n); var h=window._vaultSeamHome(n); r[n]=[s&&s.id, h&&h.loc, h&&h.mule]; });"
        "OUT.r=r;" % json.dumps(NAMES))


class DreamFaithColossal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, prelude="localStorage.setItem('d2r_ownerClaim','*');", timeout=300)["r"]

    def test_dream_and_faith_go_to_runewords(self):
        for n in ("Dream", "Faith"):
            self.assertEqual(self.r[n], ["runewords", "filed", "runewords"], n)

    def test_war_gear_stays(self):
        for n in ("Enigma", "Grief"):
            self.assertEqual(self.r[n][0], "shared", n)

    def test_every_colossal_jewel_is_war_stash_gear(self):
        for n in NAMES[4:10]:
            self.assertEqual(self.r[n][:2], ["shared", "shared"], n)


RED_PROOF = [
    {"why": "v3849 - the Colossal Ancient jewels fall back to UNI-SMALL",
     "file": "bible.html",
     "find": "COLOSSAL_JEWELS.some(function(cj){ return cj.n === String(name).trim(); })",
     "replace": "false",
     "matches": 1},
    {"why": "v3849 - Dream is war gear again (shared stash)",
     "file": "bible.html",
     "find": "    'call to arms': 'battle orders swap weapon',\n",
     "replace": "    'call to arms': 'battle orders swap weapon',\n    'dream': 'holy shock aura - PvP helm or shield',\n",
     "matches": 1},
    {"why": "v3849 - Faith is war gear again (shared stash)",
     "file": "bible.html",
     "find": "    'call to arms': 'battle orders swap weapon',\n",
     "replace": "    'call to arms': 'battle orders swap weapon',\n    'faith': 'fanaticism aura bow',\n",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
