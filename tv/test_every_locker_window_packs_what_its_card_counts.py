# -*- coding: utf-8 -*-
"""REG-3072 (GrokBot #230 on v3838, the third time in this class) - EVERY LOCKER'S WINDOW PACKS WHAT ITS CARD COUNTS.

GrokBot on v3838: the CHARMS card said 2 (Mac) and 1 (ALT) while its window said "Items 1 · Copies 0 · 0 on this mule" and
drew nothing; the SHARED STASH card said 13 / 15 while its window laid out 5 / 9. The same class as MAGIC & RARE's 23 vs 5
(REG-2850): keepers the card counts and the window never packs. Measured on the whole page in node with those shapes (two
kept grand charms and a magic-find small charm homed on CHARMS, two small charms on the shared stash): on the page before
P3b the CHARMS window said "Items 3 · Copies 0" with no tile, and the shared stash window 0 of the card's 2; P3b (REG-2971:
every keeper is a record per copy, homed by the keeper rule) packs them all. This law holds the rule for EVERY locker, not
one: on a board holding keepers of every home and hand-added items on their lockers, each roster locker's window packs as
many copies as its card draws cells, and names every one. Driven on the whole page in node. RED_PROOF below.
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

# fixture names and rolls, never his
KEEPERS = {
    "Fungal Grand Charm": {"q": "magic", "base": "Grand Charm", "mods": ["+1 to Poison and Bone Skills (Necromancer Only)"], "verdict": "keep"},
    "Lion Branded Grand Charm": {"q": "magic", "base": "Grand Charm", "mods": ["+1 to Combat Skills (Barbarian Only)"], "verdict": "keep"},
    "Serpent's Small Charm of Good Luck": {"q": "magic", "base": "Small Charm", "mods": ["+15 to Mana", "7% Better Chance of Getting Magic Items"], "verdict": "keep"},
    "Small Charm of Vita": {"q": "magic", "base": "Small Charm", "mods": ["+17 to Life"], "verdict": "keep"},
    "Shimmering Small Charm of Vita": {"q": "magic", "base": "Small Charm", "mods": ["+5% to All Resistances", "+20 to Life"], "verdict": "keep"},
    "Doom Band": {"q": "rare", "base": "Ring", "mods": ["+2 to Mana after each Kill"], "verdict": "keep"},
}
HAND = ["Nagelring", "Manald Heal", "Arreat's Face", "Buriza-Do Kyanon", "Wizardspike"]
PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n"
           "localStorage.setItem('d2r_magicFinds', %s);\n" % json.dumps(json.dumps(KEEPERS))
           + "localStorage.setItem('d2r_owned', %s);\n" % json.dumps(json.dumps(list(KEEPERS)))
           + "localStorage.setItem('d2r_copies', %s);\n" % json.dumps(json.dumps({"Small Charm of Vita": 2})))
BODY = r"""
(function(){
var W = window, K = %s, HAND = %s;
HAND.forEach(function(n){ W.vaultHandAdd(n, new Date().toISOString(), {}); H.flush(60, 3); });
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); } H.flush(60, 3);
var shelf = String((document.getElementById('vault-shelf') || {}).innerHTML || '');
var ids = []; shelf.replace(/data-vault-mule="([^"]+)"/g, function(_, id){ if (ids.indexOf(id) < 0) ids.push(id); return _; });
function card(id){ var at = shelf.indexOf('data-vault-mule="' + id + '"'), nx = at < 0 ? -1 : shelf.indexOf('data-vault-mule="', at + 10); return at < 0 ? '' : shelf.slice(at, nx < 0 ? shelf.length : nx); }
OUT.homes = {}; Object.keys(K).forEach(function(n){ OUT.homes[n] = W._mfKeeperHome(n); });
OUT.lockers = {};
ids.forEach(function(id){
  var c = card(id), cells = (c.match(/class="vm-cell[ "]/g) || []).length;
  if (!cells) return;
  var names = []; c.replace(/data-(?:vault-item|magic-find)="([^"]+)"/g, function(_, n){ n = n.replace(/&#39;/g, "'").replace(/&amp;/g, '&'); if (names.indexOf(n) < 0) names.push(n); return _; });
  try { W.openMuleCard(id); } catch (e) { OUT['openErr_' + id] = String(e && e.message || e); return; }
  H.flush(60, 3);
  var det = String((document.getElementById('vault-detail') || {}).innerHTML || '');
  var txt = det.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
  var phys = /Copies \(physical\) (\d+)/.exec(txt), total = /(\d+) total/.exec(txt);
  var dn = det.replace(/&#39;/g, "'").replace(/&amp;/g, '&');
  OUT.lockers[id] = { cells: cells, packed: phys ? +phys[1] : (total ? +total[1] : null), names: names,
                      missing: names.filter(function(n){ return dn.indexOf(n) < 0; }) };
});
OUT.errors = H.errors.slice(0, 5);
})();
""" % (json.dumps(KEEPERS), json.dumps(HAND))


class EveryLockerWindowPacksWhatItsCardCounts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertNotIn("renderErr", self.o, self.o.get("renderErr"))
        self.assertEqual(self.o["errors"], [])

    def test_the_premise_spans_every_keeper_home(self):
        homes = set(self.o["homes"].values())
        self.assertTrue({"charms", "shared", "magic-rare"} <= homes, "PREMISE: the keepers do not span every home: %r" % self.o["homes"])
        self.assertTrue({"charms", "shared", "magic-rare"} <= set(self.o["lockers"]), "PREMISE: a keeper locker drew no cell: %r" % sorted(self.o["lockers"]))
        self.assertGreaterEqual(len(self.o["lockers"]), 5, "PREMISE: too few lockers hold anything: %r" % sorted(self.o["lockers"]))

    def test_every_lockers_window_packs_as_many_copies_as_its_card_draws(self):
        bad = {k: (v["cells"], v["packed"]) for k, v in self.o["lockers"].items() if v["packed"] != v["cells"]}
        self.assertEqual(bad, {}, "card cells vs window copies, per locker: %r" % bad)

    def test_every_lockers_window_names_every_item_its_card_draws(self):
        bad = {k: v["missing"] for k, v in self.o["lockers"].items() if v["missing"]}
        self.assertEqual(bad, {}, "items a card draws that its window never lays out: %r" % bad)


RED_PROOF = [
    {"why": "REG-2971 / REG-3072 - the keepers stay out of the records pool: their windows pack none",
     "file": "bible.html",
     "find": "      try { if (typeof magicFinds === 'object' && magicFinds) Object.keys(magicFinds).forEach(function(n){ if (n && poolAll.indexOf(n) < 0) poolAll.push(n); }); } catch (eMfP) {}\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2971 / REG-3072 - a keeper homed on CHARMS is filed on MAGIC & RARE: the CHARMS window packs none",
     "file": "bible.html",
     "find": "                 && typeof muleById === 'function' && muleById(window._mfKeeperHome(name))) { kind = 'filed'; mid = window._mfKeeperHome(name); }\n",
     "replace": "                 && false) { kind = 'filed'; mid = window._mfKeeperHome(name); }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2971 / REG-3072 - a keeper on the shared stash or CHARMS is drawn twice on its card, once as a record",
     "file": "bible.html",
     "find": "        items = items.filter(function(n){ return !(Object.prototype.hasOwnProperty.call(magicFinds, n) && _mfKeeperHome(n) === m.id); });\n",
     "replace": "        void 0;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
