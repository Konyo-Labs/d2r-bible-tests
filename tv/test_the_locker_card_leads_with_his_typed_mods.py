# -*- coding: utf-8 -*-
"""v3855 C3 (Elad 2026-11-02) - THE LOCKER'S HOVER CARD LEADS WITH HIS TYPED MODS, AS THE ZOOMED WINDOW DOES.

The zoomed mule window's in-game box led with the mods typed in Edit mods; the locker card for a unique, a set piece or a
rare printed the catalogue lines. One rule (_typedModsOf / _cardLeadsWithTypedMods) now feeds both cards: typed mods lead,
marked data-mod-manual, ranges drop once typed, and an item with nothing typed reads exactly as before.
Whole page in node: _arttipResolve before and after a typed save.
"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

OWNED = ["Harlequin Crest (Shako)", "Tal Rasha's Guardianship", "Grief"]
KEEP = {"Storm Cry Ring": {"q": "rare", "base": "Ring"}}
PRELUDE = ("localStorage.setItem('d2r_ownerClaim','*');localStorage.setItem('d2r_owned', %s);"
           "localStorage.setItem('d2r_magicFinds', %s);") % (json.dumps(json.dumps(OWNED)), json.dumps(json.dumps(KEEP)))
TYPED = "+2 To All Skills (typed)"
BODY = r"""
var W = window; W.renderVault(); H.flush(60, 3);
var names = %NAMES%; OUT.before = {}; OUT.after = {};
names.forEach(function(n){ OUT.before[n] = String((W._arttipResolve(n) || {}).desc || ''); });
names.forEach(function(n){ W._vaultSetManualMods(n, [%TYPED%, 'Second line']); });
names.forEach(function(n){ OUT.after[n] = String((W._arttipResolve(n) || {}).desc || ''); });
OUT.zoomSame = typeof W._typedModsOf === 'function' && JSON.stringify(W._typedModsOf(names[0])) === JSON.stringify(W._vaultManualMods(names[0]));
"""
NAMES = ["Harlequin Crest (Shako)", "Tal Rasha's Guardianship", "Storm Cry Ring"]
_OUT = None


def out():
    global _OUT
    if _OUT is None:
        _OUT = VPN.run(BODY.replace('%NAMES%', json.dumps(NAMES)).replace('%TYPED%', json.dumps(TYPED)), prelude=PRELUDE, timeout=300)
    return _OUT


class TheLockerCardLeadsWithHisMods(unittest.TestCase):
    def test_nothing_typed_reads_as_before(self):
        for n in NAMES:
            self.assertNotIn("data-mod-manual", out()["before"][n], n)
            self.assertTrue(out()["before"][n], n)

    def test_typed_mods_lead_the_card(self):
        for n in NAMES:
            d = out()["after"][n]
            self.assertIn("data-mod-manual", d, n)
            self.assertIn("(typed)", d, n)
            first_aff = d.find('<div class="att-aff')
            self.assertEqual(d.find('data-mod-manual'), d.find('data-mod-manual', first_aff), (n, d[:400]))
            self.assertTrue(d.find('data-mod-manual') - first_aff < 60, (n, d[:400]))
            self.assertNotIn('data-mod-range="1"', d, n)

    def test_one_rule_feeds_both_cards(self):
        self.assertTrue(out()["zoomSame"])
        src = open(os.path.join(HERE, "..", "bible.html"), encoding="utf-8").read()
        self.assertIn("window._typedModsOf(n)", src)
        self.assertIn("return _cardLeadsWithTypedMods(nm, _arttipResolveCatalogue(nm));", src)


RED_PROOF = [
    {"why": "the locker card skips his typed mods", "file": "bible.html",
     "find": "function _arttipResolve(nm){ return _cardLeadsWithTypedMods(nm, _arttipResolveCatalogue(nm)); }",
     "replace": "function _arttipResolve(nm){ return _arttipResolveCatalogue(nm); }", "matches": 1},
    {"why": "typed mods trail the catalogue lines", "file": "bible.html",
     "find": "  d = cut >= 0 ? d.slice(0, cut) + block + d.slice(cut) : d + block;", "replace": "  d = d + block;", "matches": 1},
    {"why": "typed mods are not marked as his", "file": "bible.html",
     "find": "'<div class=\"att-aff att-var\" data-mod-manual=\"1\">' + String(l)", "replace": "'<div class=\"att-aff att-var\">' + String(l)", "matches": 1},
]

if __name__ == "__main__":
    unittest.main()
