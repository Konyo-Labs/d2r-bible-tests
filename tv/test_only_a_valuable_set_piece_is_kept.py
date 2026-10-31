# -*- coding: utf-8 -*-
"""v3849 (Elad 2026-10-31 16:39/16:40) - ONLY A VALUABLE SET PIECE IS KEPT; every other set piece is a ruled throw-out.

Kept: a piece the repo's trade table (window.ITEM_VALUE) prices high or med - Tal Rasha's pieces, Guillaume's Face,
Bul-Kathos' Wedding Band, Immortal King's Soul Cage, M'avina's True Sight, Griswold's Honor/Redemption,
Trang-Oul's Claws/Girth - plus Naj's Puzzler (his 16:39 ruling), Laying of Hands (v1972) and Horazon's Splendor (v440).
Kept pieces go to a sets mule, a sister piece's mule first. The rest of Naj's, Sazabi's, Sigon's, Immortal King's
low pieces and every other set piece go to the throw-out pile with a ruled reason, never "by DEFAULT".
"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

KEEP = ["Naj's Puzzler", "Tal Rasha's Lidless Eye", "Tal Rasha's Fine-Spun Cloth", "Guillaume's Face",
        "Bul-Kathos' Wedding Band", "Immortal King's Soul Cage", "Griswold's Honor", "Trang-Oul's Claws",
        "Laying of Hands"]
THROW = ["Naj's Circlet", "Naj's Light Plate", "Sazabi's Ghost Liberator", "Sigon's Visor",
         "Immortal King's Will", "Aldur's Stony Gaze", "Arcanna's Head", "Trang-Oul's Wing"]

BODY = r"""
var r = {};
%(names)s.forEach(function(n){ var m = suggestMule(n) || {}; r[n] = { id: m.id, why: String(m.why || '') }; });
OUT.r = r;
""" % {"names": json.dumps(KEEP + THROW)}

PRELUDE = "localStorage.setItem('d2r_ownerClaim','*');"

RED_PROOF = [
    {"matches": 1, "file": "bible.html", "why": "the trade table is not read: valuable pieces go out",
     "find": "      return v === 'high' || v === 'med' || _KEEP_PIECE.test(p)",
     "replace": "      return _KEEP_PIECE.test(p)"},
    {"matches": 1, "file": "bible.html", "why": "low pieces are kept too",
     "find": "      return v === 'high' || v === 'med' || _KEEP_PIECE.test(p)",
     "replace": "      return !!v || _KEEP_PIECE.test(p)"},
    {"matches": 1, "file": "bible.html", "why": "Naj's Puzzler ruling dropped",
     "find": "    var _KEEP_PIECE = /^(Naj's Puzzler|Laying of Hands)$/i;",
     "replace": "    var _KEEP_PIECE = /^(Laying of Hands)$/i;"},
    {"matches": 1, "file": "bible.html", "why": "the piece branch keeps by set name again",
     "find": "        if (!_keptPiece(name, psn)) return",
     "replace": "        if (!/Tal Rasha|Immortal King|Griswold|Aldur|Trang.?Oul|Natalya|M.?avina|Horazon|Disciple|Orphan|Naj/i.test(psn)) return"},
]


class OnlyAValuableSetPieceIsKept(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, prelude=PRELUDE, timeout=300)["r"]

    def test_a_valuable_piece_goes_to_a_sets_mule(self):
        for n in KEEP:
            if n in ("Guillaume's Face", "Bul-Kathos' Wedding Band"):
                continue    # war gear / high trade value keep close in the shared stash (older rulings) - checked below
            self.assertIn(self.r[n]["id"], ("sets-major", "sets-rest"), (n, self.r[n]))

    def test_the_shared_stash_keepers_are_kept(self):
        for n in ("Guillaume's Face", "Bul-Kathos' Wedding Band"):
            self.assertEqual(self.r[n]["id"], "shared", (n, self.r[n]))

    def test_every_other_piece_is_a_ruled_throw_out(self):
        for n in THROW:
            self.assertEqual(self.r[n]["id"], "__throwout", (n, self.r[n]))
            self.assertIn("low set piece", self.r[n]["why"], n)
            self.assertNotIn("DEFAULT", self.r[n]["why"], n)


if __name__ == "__main__":
    unittest.main()
