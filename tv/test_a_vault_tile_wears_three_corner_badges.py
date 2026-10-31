# -*- coding: utf-8 -*-
"""v3849 D2 (Elad 2026-10-31 12:22) - EVERY VAULT TILE WEARS THREE CORNER BADGES, AND EDITING MODS NEVER MOVES THE ITEM.

The pencil (top-left) opens one box for the item's mods, the magnifier (bottom-left) is the evidence door and $
(bottom-right) asks the d2jsp price. Saving mods writes only the typed-mods store: the item's records (mule, locker,
cell), assign and owned read the same before and after. A shadow draws no pencil and refuses a save.
Measured on the whole page in node: renderVault, the records, a save, a second paint.
"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

KEEP = {"Small Charm of Balance": {"q": "magic", "base": "Small Charm"}}
PRELUDE = ("localStorage.setItem('d2r_ownerClaim','*');"
           "localStorage.setItem('d2r_owned', %s);"
           "localStorage.setItem('d2r_magicFinds', %s);"
           "localStorage.setItem('d2r_muleAssign', JSON.stringify({'Harlequin Crest':'uni-armor','Arachnid Mesh':'uni-armor'}));") % (json.dumps(json.dumps(["Harlequin Crest", "Arachnid Mesh"])),
                                                              json.dumps(json.dumps(KEEP)))

BODY = r"""
var W = window;
function snap(){
  var rec = {};
  ['Harlequin Crest','Arachnid Mesh'].forEach(function(n){ var h = W._vaultSeamHome(n); rec[n] = JSON.stringify(h); });
  return JSON.stringify({ rec: rec, assign: localStorage.getItem('d2r_muleAssign'), pos: localStorage.getItem('d2r_mulePos'), owned: localStorage.getItem('d2r_owned'),
                          mf: Object.keys(magicFinds).sort() });
}
function cellOf(html, n){
  var parts = html.split('<div class="vm-cell');
  for (var k = 1; k < parts.length; k++){
    var head = parts[k].slice(0, 600);
    if (head.indexOf('data-vault-item="' + n + '"') >= 0 || head.indexOf('data-magic-find="' + n + '"') >= 0 || head.indexOf('data-arttip="' + n + '"') >= 0) return parts[k];
  }
  return '';
}W.renderVault(); H.flush(60, 3);
function shelf(){ var out = [String((document.getElementById('vault-shelf')||{}).innerHTML||'')]; ['uni-armor','magic-rare','charms','shared'].forEach(function(id){ try { W.openMuleCard(id); H.flush(60, 3); } catch (e) {} out.push(String((document.getElementById('vault-detail')||{}).innerHTML||'')); }); return out.join('\n'); }
var html = shelf();
OUT.cell = cellOf(html, 'Arachnid Mesh');
OUT.mcell = cellOf(html, 'Small Charm of Balance');
OUT.before = snap();
OUT.saved = W._vaultModsSave('Arachnid Mesh', '+2 to All Skills\n141 Defense\n');
OUT.saved2 = W._vaultModsSave('Small Charm of Balance', '+5% Faster Hit Recovery\n+20 to Life');
W.renderVault(); H.flush(60, 3);
OUT.after = snap();
OUT.manual = W._vaultManualMods('Arachnid Mesh');
OUT.tip = String(_mfTipHtml('Small Charm of Balance'));
W._tvdShadow = { owner: 'x' };
W.renderVault(); H.flush(60, 3);
OUT.shCell = cellOf(shelf(), 'Arachnid Mesh');
OUT.shSave = W._vaultModsSave('Arachnid Mesh', 'hacked');
OUT.shOpen = W._vaultModsEdit('Arachnid Mesh');
OUT.manual2 = W._vaultManualMods('Arachnid Mesh');
"""


class CornerBadges(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_three_badges_on_catalogue_and_magic_tiles(self):
        for c in (self.o["cell"], self.o["mcell"]):
            self.assertTrue(c, "the tile was not drawn")
            self.assertIn('class="vm-cell-edit"', c)
            self.assertIn('vm-cell-ev', c)
            self.assertIn('class="vm-cell-price"', c)

    def test_a_mod_save_moves_nothing(self):
        self.assertTrue(self.o["saved"] and self.o["saved2"])
        self.assertEqual(self.o["before"], self.o["after"])
        self.assertEqual(self.o["manual"], ["+2 to All Skills", "141 Defense"])

    def test_typed_mods_replace_the_ranges(self):
        self.assertIn("+20 to Life", self.o["tip"])
        self.assertNotIn('data-mod-range="1"', self.o["tip"])

    def test_a_shadow_has_no_pencil_and_cannot_save(self):
        self.assertTrue(self.o["shCell"])
        self.assertNotIn('vm-cell-edit', self.o["shCell"])
        self.assertIn('vm-cell-price', self.o["shCell"])
        self.assertFalse(self.o["shSave"])
        self.assertFalse(self.o["shOpen"])
        self.assertEqual(self.o["manual2"], ["+2 to All Skills", "141 Defense"])


RED_PROOF = [
    {"why": "v3849 D2 - the pencil is drawn in a shadow",
     "file": "bible.html",
     "find": "function _vaultCornerEdit(n){\n  if (_vaultInShadow()) return '';\n",
     "replace": "function _vaultCornerEdit(n){\n",
     "matches": 1},
    {"why": "v3849 D2 - a mod save also re-files the item",
     "file": "bible.html",
     "find": "  return _vaultSetManualMods(name, String(text == null ? '' : text).split(/\\r?\\n/));\n",
     "replace": "  try { var _ra = JSON.parse(localStorage.getItem('d2r_muleAssign') || '{}'); _ra[name] = 'uni-small'; localStorage.setItem('d2r_muleAssign', JSON.stringify(_ra)); } catch (eX) {}\n  return _vaultSetManualMods(name, String(text == null ? '' : text).split(/\\r?\\n/));\n",
     "matches": 1},
    {"why": "v3849 D2 - the $ badge is not on the catalogue tile",
     "file": "bible.html",
     "find": "          + _vaultCornerPrice(n) + _lockTag\n",
     "replace": "          + _lockTag\n",
     "matches": 1},
    {"why": "v3849 D2 - typed mods do not override",
     "file": "bible.html",
     "find": "var _man = _vaultManualMods(name); if (_man && _man.length) return _man; ",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
