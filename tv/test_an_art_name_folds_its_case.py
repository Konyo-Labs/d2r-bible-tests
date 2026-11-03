# -*- coding: utf-8 -*-
"""REG-3029 (v3837's render gate) - AN ART NAME FOLDS ITS CASE, SO A BASE SPELLED THE GAME'S WAY KEEPS ITS PICTURE.

The vault files a base by the game's spelling "Silver-edged Axe"; the art table keys "Silver-Edged Axe". artUrl matched
exactly, so it missed, and once REG-2904 made a vault cell draw artOr's answer, the card drew the missing-art mark where
v3836 drew the axe - the render gate blocked v3837's push on that mark, cut inside the UNI-WEAPONS card, at every width.
artUrl now folds the case as a lookup fallback (like the v2762 apostrophe fold): exact first, and a fold answers only
when it names ONE key - two keys that differ only by case are ambiguous and draw no picture. Driven on the whole page in
node (vault_page_node - never a browser on his Mac). RED_PROOF below.
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"

BODY = r"""
var W = window;
OUT.exact = W.artUrl('Silver-Edged Axe');
OUT.folded = W.artUrl('Silver-edged Axe');
OUT.none = W.artUrl('No Such Item At All');
D2IO_ART['Zz Fold Twin'] = 'art/a.png'; D2IO_ART['zz fold twin'] = 'art/b.png';
OUT.ambiguous = W.artUrl('ZZ FOLD TWIN');
OUT.exactTwin = W.artUrl('zz fold twin');
W._vaultAutoIntakeSet && W._vaultAutoIntakeSet(false);
var h = W.vaultHandAdd('Silver-Edged Axe', undefined, { by: 'the law' }); W.vaultAssign((h && h.name) || 'Silver-Edged Axe', 'uni-weap');
W.renderVault(); H.flush(60, 3);
var s = (document.getElementById('vault-shelf') || {}).innerHTML || '';
var i = s.search(/data-vault-item="Silver-[Ee]dged Axe"/);
var cell = i < 0 ? '' : s.slice(i, s.indexOf('</span></span>', i) + 14);
OUT.cell = { found: i >= 0, filedAs: (cell.match(/data-vault-item="([^"]+)"/) || [])[1] || null,
             img: (cell.match(/<img class="d2art-img" src="([^"]+)"/) || [])[1] || null, mark: /d2art-failed"/.test(cell) };
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AnArtNameFoldsItsCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, prelude=CLAIM, timeout=300)

    def test_a_base_spelled_the_games_way_draws_its_picture(self):
        r = self.r
        self.assertEqual(r["__boot"]["errors"], [], r["__boot"])
        self.assertTrue(r["exact"], "PREMISE: the art table has no picture for Silver-Edged Axe at all: %r" % r)
        self.assertEqual(r["folded"], r["exact"], "the game's spelling Silver-edged Axe misses the picture: %r" % r)
        self.assertIsNone(r["none"], "a name with no art drew a picture: %r" % r["none"])

    def test_a_fold_that_names_two_keys_draws_no_picture(self):
        r = self.r
        self.assertEqual(r["exactTwin"], "art/b.png", "PREMISE: the exact spelling does not answer first: %r" % r)
        self.assertIsNone(r["ambiguous"], "a case fold that names two keys guessed one: %r" % r["ambiguous"])

    def test_the_vault_cell_of_a_filed_base_draws_the_base(self):
        c = self.r["cell"]
        self.assertTrue(c["found"], "PREMISE: the filed base has no vault cell: %r" % c)
        self.assertEqual((c["img"], c["mark"]), (self.r["exact"], False),
                         "the vault cell of %r drew the missing-art mark, not its base: %r" % (c["filedAs"], c))


RED_PROOF = [
    {"why": "REG-3029 - artUrl matches the exact case only, so the game's spelling of a base draws the missing-art mark",
     "file": "bible.html",
     "find": "  if (!direct) try {\n    var _lc = String(name || '').toLowerCase();\n",
     "replace": "  if (false) try {\n    var _lc = String(name || '').toLowerCase();\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3029 - an ambiguous case fold guesses the first key",
     "file": "bible.html",
     "find": "_m[l] = (l in _m) ? null : k;",
     "replace": "_m[l] = (l in _m) ? _m[l] : k;",
     "matches": 1, "needs": "node"},
    {"why": "v3859 - the codex spells the base the game's way, the base-sprite pass looks BASE_DB up exactly, so the axe loses its picture",
     "file": "bible.html",
     "find": "        _bb = _bFold[_bb.toLowerCase()] || '';\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
