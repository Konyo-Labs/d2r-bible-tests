# -*- coding: utf-8 -*-
"""v3855 (Elad) - THE PENCIL OPENS EDIT MODS ON EVERY VAULT CELL, IN THE LOCKER AND IN THE ZOOMED MULE / SHARED STASH.

The pencil showed its tip and opened nothing: the Edit mods box sat at z-index 9000, under the mule window (99997) and
the evidence panel (99980). The zoomed mule window drew no $ and no pencil at all - the locker tile and the zoomed tile
were two copies. Now both draw _vaultItemBadges, the box is the topmost layer and last in the body, a press on a badge
never starts a drag, and the card shows his typed mods. A batch of kinds: unique, set piece, runewords (Grief, Enigma),
rare and magic, charms (small, grand, Torch, Annihilus), jewel, socketed base, base, rune - and (v3855 C4) one item on
EVERY mule of the roster plus the Shared Stash. Clicking edit opens that item's box; Cancel leaves it in
place. Measured on the whole page in node.
"""
import json, os, re, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

ITEMS = ["Harlequin Crest", "Arachnid Mesh", "Tal Rasha's Guardianship", "Grief", "Enigma", "Hellfire Torch",
         "Annihilus", "Monarch", "Ber Rune",
         # v3855 C4 - a socketed item, and one item filed on EVERY mule of the roster (MULE_ITEM)
         "Socketed Helm (2os)", "Guillaume's Face", "Windforce", "Stone of Jordan", "Spirit", "Gheed's Fortune",
         "Skin of the Vipermagi", "Herald of Zakarum"]
KEEP = {"Small Charm of Balance": {"q": "magic", "base": "Small Charm"}, "Doom Spiral": {"q": "rare", "base": "Ring"},
        "Ruby Jewel of Fervor": {"q": "magic", "base": "Jewel"}, "Grand Charm of Vita": {"q": "magic", "base": "Grand Charm"}}
#: v3855 C4 - every mule of DEFAULT_ROSTER, and the item filed on it (the Shared Stash and the keeper lockers by their rule)
MULE_ITEM = {"sets-major": "Tal Rasha's Guardianship", "sets-rest": "Guillaume's Face", "uni-weap": "Windforce",
             "uni-armor": "Arachnid Mesh", "uni-small": "Stone of Jordan", "runewords": "Spirit", "bases": "Monarch",
             "magic-rare": "Doom Spiral", "charms": "Gheed's Fortune", "shared": "Annihilus", "dupes": "Skin of the Vipermagi",
             "wip": "Herald of Zakarum"}
ASSIGN = dict((n, m) for m, n in MULE_ITEM.items() if m not in ("magic-rare", "shared"))
PRELUDE = ("localStorage.setItem('d2r_ownerClaim','*');localStorage.setItem('d2r_owned', %s);"
           "localStorage.setItem('d2r_magicFinds', %s);localStorage.setItem('d2r_muleAssign', %s);") % (
    json.dumps(json.dumps(ITEMS)), json.dumps(json.dumps(KEEP)), json.dumps(json.dumps(ASSIGN)))

BODY = r"""
var W = window, NAMES = %s;
W._vaultModsSave('Arachnid Mesh', '+2 to All Skills\n141 Defense');
W.renderVault(); H.flush(60, 3);
function unq(s){ return String(s).replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&'); }
function homes(){ var o = {}; NAMES.forEach(function(n){ try { o[n] = JSON.stringify(W._vaultSeamHome(n)); } catch (e) { o[n] = 'ERR'; } }); return JSON.stringify(o); }
function pieces(html, open){
  var out = {}, parts = String(html).split(open);
  for (var k = 1; k < parts.length; k++){
    var p = parts[k], m = /data-(?:vault-item|magic-find|arttip)="([^"]+)"/.exec(p.slice(0, 900)) || /title="([^"(]+) \(/.exec(p.slice(0, 600));
    if (m){ var end = p.indexOf('<div class="vd-item'); out[unq(m[1])] = end > 0 ? p.slice(0, end) : p.slice(0, 4000); }
  }
  return out;
}
function press(cellHtml){
  var m = /class="vm-cell-edit[^"]*"[^>]*onclick="([^"]+)"/.exec(cellHtml); if (!m) return 'no pencil';
  var host = document.getElementById('vault-mods-edit'); if (host) host.hidden = true;
  try { new Function('event', unq(m[1]))({ stopPropagation: function(){} }); } catch (e) { return 'threw ' + e; }
  host = document.getElementById('vault-mods-edit');
  if (!host || host.hidden) return 'no box';
  var said = { item: host.dataset && host.dataset.item, text: String((document.getElementById('vme-text') || {}).value || (host.innerHTML.match(/<textarea[^>]*>([^<]*)/) || [,''])[1]) };
  var c = document.getElementById('vme-cancel'); if (c && c.onclick) c.onclick();
  said.closed = !!host.hidden;
  return said;
}
var before = homes();
OUT.locker = {}; OUT.zoom = {};
var shelf = String((document.getElementById('vault-shelf') || {}).innerHTML || '');
var lc = pieces(shelf, '<div class="vm-cell');
Object.keys(lc).forEach(function(n){ OUT.locker[n] = { edit: lc[n].indexOf('vm-cell-edit') >= 0, price: lc[n].indexOf('vm-cell-price') >= 0, edited: lc[n].indexOf('vmb-edited') >= 0, press: press(lc[n]) }; });
var mules = {}; NAMES.forEach(function(n){ try { var h = W._vaultSeamHome(n); if (h && h.mule) mules[h.mule] = 1; } catch (e) {} });
['shared', 'magic-rare', 'charms'].concat(%MULES%).forEach(function(m){ mules[m] = 1; });
OUT.mules = Object.keys(mules);
OUT.mules.forEach(function(m){
  try { W.openMuleCard(m); H.flush(60, 3); } catch (e) { return; }
  var d = document.getElementById('vault-detail'), z = pieces(String(d && d.innerHTML || ''), '<div class="vd-item');
  Object.keys(z).forEach(function(n){ OUT.zoom[m + '|' + n] = { edit: z[n].indexOf('vm-cell-edit') >= 0, price: z[n].indexOf('vm-cell-price') >= 0, edited: z[n].indexOf('vmb-edited') >= 0, press: press(z[n]) }; });
});
OUT.same = before === homes();
OUT.rune = W._vaultItemBadges("Ber Rune"); OUT.gem = W._vaultItemBadges("Perfect Amethyst"); OUT.shako = W._vaultItemBadges("Harlequin Crest"); OUT.base = W._vaultItemBadges("Monarch");
OUT.place = [[100,100,60,120],[10,10,30,30],[900,300,122,184],[500,20,60,60],[10,300,60,184]].map(function(a){
  var r = { left: a[0], top: a[1], width: a[2], height: a[3], right: a[0] + a[2], bottom: a[1] + a[3] };
  var p = W._d2TipPlace(r, 320, 520, 1280, 720, 8);
  return { hit: !(p.x + 320 <= r.left || p.x >= r.right || p.y + 520 <= r.top || p.y >= r.bottom), side: p.side, on: p.x >= 0 && p.y >= 0 };
});
""".replace("%MULES%", json.dumps(sorted(MULE_ITEM))) % json.dumps(ITEMS + list(KEEP))

NO_PENCIL = {"Ber Rune"}


class PencilEverywhere(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def _check(self, where, rows):
        self.assertTrue(rows, "%s drew no item" % where)
        for key, r in rows.items():
            n = key.split("|")[-1]
            self.assertTrue(r["price"], "%s %s has no $" % (where, key))
            if n in NO_PENCIL:
                self.assertFalse(r["edit"], "%s %s has nothing to edit, yet wears a pencil" % (where, key))
                continue
            self.assertTrue(r["edit"], "%s %s has no pencil" % (where, key))
            self.assertIsInstance(r["press"], dict, "%s %s: %s" % (where, key, r["press"]))
            self.assertEqual(r["press"]["item"], n, key)
            self.assertTrue(r["press"]["closed"], key)

    def test_locker_cells(self):
        self._check("locker", self.o["locker"])

    def test_zoomed_cells_wear_the_same_pair(self):
        self._check("zoom", self.o["zoom"])
        self.assertTrue(any(k.startswith("shared|") for k in self.o["zoom"]), "the Shared Stash drew nothing")

    def test_typed_mods_mark_the_pencil_and_fill_the_box(self):
        both = [r for k, r in list(self.o["locker"].items()) + list(self.o["zoom"].items()) if k.split("|")[-1] == "Arachnid Mesh"]
        self.assertTrue(both)
        for r in both:
            self.assertTrue(r["edited"])
            self.assertIn("141 Defense", r["press"]["text"])

    def test_every_mule_and_the_shared_stash_draw_their_item_with_badges(self):
        for m, n in sorted(MULE_ITEM.items()):
            r = self.o["zoom"].get(m + "|" + n)
            self.assertIsNotNone(r, "the %s window drew no %s (drew %s)" % (m, n, sorted(k for k in self.o["zoom"] if k.startswith(m + "|"))))
            self.assertTrue(r["price"] and r["edit"], (m, n, r))
            self.assertIsInstance(r["press"], dict, (m, n, r["press"]))

    def test_a_jewel_a_grand_charm_and_a_socketed_item_wear_the_pencil(self):
        for n in ("Ruby Jewel of Fervor", "Grand Charm of Vita", "Socketed Helm (2os)"):
            rows = [r for k, r in list(self.o["locker"].items()) + list(self.o["zoom"].items()) if k.split("|")[-1] == n]
            self.assertTrue(rows, "%s is drawn nowhere" % n)
            for r in rows:
                self.assertTrue(r["edit"] and r["price"], (n, r))
                self.assertIsInstance(r["press"], dict, (n, r["press"]))
                self.assertEqual(r["press"]["item"], n)

    def test_relevance(self):
        for k in ("rune", "gem"):
            self.assertNotIn("vm-cell-edit", self.o[k], k)
            self.assertIn("vm-cell-price", self.o[k], k)
        for k in ("shako", "base"):
            self.assertIn("vm-cell-edit", self.o[k], k)

    def test_nothing_moves(self):
        self.assertTrue(self.o["same"])

    def test_the_card_never_covers_its_item(self):
        for p in self.o["place"]:
            self.assertFalse(p["hit"], p)
            self.assertTrue(p["on"], p)


class Static(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8") as f:
            self.src = f.read()

    def test_the_box_is_the_top_layer(self):
        z = int(re.search(r"\.vault-mods-edit\{position:fixed;inset:0;z-index:(\d+)", self.src).group(1))
        self.assertGreater(z, 99997)

    def test_badges_are_faint_small_and_corner_tight(self):
        rule = re.search(r"\.vm-cell-edit,\.vm-cell-price\{([^}]*)\}", self.src).group(1)
        self.assertIn("width:14px", rule); self.assertIn("height:14px", rule)
        op = float(re.search(r"opacity:([.\d]+)", rule).group(1))
        self.assertTrue(0 < op <= 0.3, op)
        self.assertIn(".vm-cell-edit{left:2px;top:2px}", self.src)
        self.assertIn(".vm-cell-price{right:2px;bottom:2px;", self.src)

    def test_the_whole_cell_is_the_hover(self):
        self.assertIn("var _vcell = e.target.closest('.vm-cell[data-arttip]');", self.src)
        self.assertIn("if (!(el.classList && el.classList.contains('vm-cell')) && (_rr.width > 430 || _rr.height > 120)) return;", self.src)


RED_PROOF = [
    {"why": "a keeper on the CHARMS mule is packed nowhere (the C2 span)", "file": "bible.html",
     "find": "if (n && _mfKeeperHome(n) === muleId && !Object", "replace": "if (false && n && _mfKeeperHome(n) === muleId && !Object", "matches": 1},
    {"why": "a jewel wears no pencil", "file": "bible.html",
     "find": "  var ed = _vaultModsEditable(n) ? _vaultCornerEdit(n) : '';", "replace": "  var ed = (_vaultModsEditable(n) && !/Jewel/.test(n)) ? _vaultCornerEdit(n) : '';", "matches": 1},
    {"why": "the Edit mods box goes back under the mule window", "file": "bible.html",
     "find": ".vault-mods-edit{position:fixed;inset:0;z-index:99999;", "replace": ".vault-mods-edit{position:fixed;inset:0;z-index:9000;", "matches": 1},
    {"why": "the zoomed mule window loses $ and the pencil", "file": "bible.html",
     "find": "        + (typeof window._vaultItemBadges === 'function' ? window._vaultItemBadges(p.n) : '')   /* v3855 - the locker's own badge pair */\n",
     "replace": "", "matches": 1},
    {"why": "a rune wears a pencil", "file": "bible.html",
     "find": "  var ed = _vaultModsEditable(n) ? _vaultCornerEdit(n) : '';", "replace": "  var ed = _vaultCornerEdit(n);", "matches": 1},
    {"why": "typed mods no longer mark the pencil", "file": "bible.html",
     "find": "ed = ed.replace('class=\"vm-cell-edit\"', 'class=\"vm-cell-edit vmb-edited\"');", "replace": "ed = ed;", "matches": 1},
    {"why": "the card goes back to sitting on the item when it fits neither above nor below", "file": "bible.html",
     "find": "return { x: r.right + g, y: cy(r.top + r.height / 2 - th / 2), side: 'right' };", "replace": "return { x: r.left, y: cy(r.top), side: 'right' };", "matches": 1},
    {"why": "a tall tile is refused as a hover again", "file": "bible.html",
     "find": "if (!(el.classList && el.classList.contains('vm-cell')) && (_rr.width > 430 || _rr.height > 120)) return;",
     "replace": "if (_rr.width > 430 || _rr.height > 120) return;", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
