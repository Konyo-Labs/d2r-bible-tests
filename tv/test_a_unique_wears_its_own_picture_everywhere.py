# -*- coding: utf-8 -*-
"""#111 (REG-2805) - HIS RULING 2026-10-28 (b): EACH UNIQUE SHOWS ITS OWN PICTURE, THE SAME ON EVERY SURFACE.

v406 put every unique and set piece in its table onto its BASE's sprite from the game files, on the note that D2R has no
picture of its own for a unique. Measured on the repo's own art (the whole page in node): of the 398 uniques
tv/unique_roster.json names, 288 drew their base's plain sprite (Nightwing's Veil a Great Helm, Harlequin Crest a Cap) while
280 of them had their own icon registered (art/mr_*.png - the base sprite in that unique's own in-game colour), and the
game files do carry a sprite of its own for 69 (v384's extraction: Lightsabre, The Minotaur...).

ONE resolver, window._keeperArt, now answers for every name in that table, in this order - its own sprite from the game
files, its own icon, its base's sprite as the stated fallback - and D2IO_ART holds the answer. artUrl asks it first, so the
vault cell and the rows (artOr), the hover (_arttipResolve -> artUrl), the locker and mule cards, the console's copy of
D2IO_ART and the bridge's art fields all draw the one picture. Driven here: a unique with its own icon, one with its own
sprite, one with neither (the fallback), the two names the old label rules and the runeword table turned into another item,
the roster-wide rule, and each surface. RED_PROOF below.
"""
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

NW, LS, GA, EE, BK, CM = ("Nightwing's Veil", "Lightsabre", "Goldstrike Arch", "Ethereal Edge", "Bul-Kathos' Wedding Band",
                          "Crescent Moon")
ROSTER = json.load(io.open(os.path.join(HERE, "unique_roster.json"), encoding="utf-8"))["names"]

PRELUDE = ("localStorage.setItem('d2r_ownerClaim', '*');\n"
           "localStorage.setItem('d2r_owned', %s);\n" % json.dumps(json.dumps([NW, LS]))
           + "localStorage.setItem('d2r_muleAssign', %s);\n" % json.dumps(json.dumps({NW: "uni-armor", LS: "uni-weap"})))

BODY = r"""
(function(){
var W = window, ROSTER = %s, NAMES = %s;
function rowSrc(n){ var m = /src="([^"]+)"/.exec(artOr(n, '', 'sm') || ''); return m ? m[1] : null; }
/* REG-2847 - the hover's OWN picture line (arttip: built base, then artUrl(name), then the resolver's artName) - the old model
   read artUrl(artName) alone, which the hover draws only when the name itself has no picture */
function hoverSrc(n){ var r = _arttipResolve(n) || {}; return (r.builtBase && artUrl(r.artName)) || artUrl(n) || (r.artName ? artUrl(r.artName) : null) || null; }
OUT.one = {};
NAMES.concat(['Crescent Moon (amulet)', "Sander's Riprap", 'Crescent Moon (sword)']).forEach(function(n){
  OUT.one[n] = { k: W._keeperArt(n), artUrl: artUrl(n), row: rowSrc(n), hover: hoverSrc(n), table: D2IO_ART[n] || null };
});
/* the cards: the locker card's cell and the mule card's cell for a filed item */
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); }
H.flush(60, 3);
function cellSrc(html, n){
  var at = html.indexOf('data-arttip="' + n.replace(/'/g, '&#39;') + '"');
  if (at < 0) at = html.indexOf('data-arttip="' + n + '"');
  if (at < 0) return 'no cell';
  var m = /src="([^"]+)"/.exec(html.slice(at, at + 1500));
  return m ? m[1].split('?')[0] : 'no img';
}
var shelf = String((document.getElementById('vault-shelf') || {}).innerHTML || '');
OUT.card = { nw: cellSrc(shelf, %s), ls: cellSrc(shelf, %s) };
try { W.openMuleCard('uni-armor'); } catch (e) { OUT.openErr = String(e && e.message || e); }
H.flush(60, 3);
var dh = String((document.getElementById('vault-detail') || {}).innerHTML || ''), mn = %s;
var vd = dh.indexOf('class="vd-item vd-r-unique" style="');
var vdAt = dh.indexOf('title="' + mn.replace(/'/g, '&#39;') + ' (', vd < 0 ? 0 : vd);
var vdM = vdAt < 0 ? null : /src="([^"]+)"/.exec(dh.slice(vdAt, vdAt + 1500));
OUT.mule = vdAt < 0 ? 'no cell' : (vdM ? vdM[1].split('?')[0] : 'no img');
/* the roster: what each unique the table knows draws, and what its own icon / sprite would be */
OUT.roster = {};
ROSTER.forEach(function(n){
  var k = W._keeperArt(n);
  if (!k) { OUT.roster[n] = null; return; }
  OUT.roster[n] = { from: k.from, url: k.url, artUrl: artUrl(n), row: rowSrc(n), table: D2IO_ART[n] || D2IO_ART[n.replace(/’/g, "'")] || null,
                    own: _KEEPER_ART.own[n] || _KEEPER_ART.own[n.replace(/’/g, "'")] || null,
                    icon: _KEEPER_ART.icon[n] || _KEEPER_ART.icon[n.replace(/’/g, "'")] || null };
});
/* every unique the roster names, in or out of the table: the row's picture and the hover's */
OUT.pair = {};
ROSTER.forEach(function(n){ OUT.pair[n] = [rowSrc(n), hoverSrc(n)]; });
OUT.renewed = ['Renewed Cold Rupture', 'Renewed Black Cleft', 'Latent Cold Rupture'].map(function(n){ return [n, rowSrc(n), hoverSrc(n)]; });
OUT.kinds = {};
Object.keys(D2IO_ART).forEach(function(k){
  var t = (typeof ITEM_TIP !== 'undefined') ? ITEM_TIP[k] : null, c = (typeof ITEM_CODEX !== 'undefined') ? ITEM_CODEX[k] : null;
  var x = (typeof EXTRA_ITEMS !== 'undefined') ? EXTRA_ITEMS[k] : null;
  var kind = (t && t.t) || (c && c.rarity) || (x && x.rarity) || null;
  if (kind) OUT.kinds[k] = [artUrl(k), String(kind).toLowerCase()];
});
OUT.errors = H.errors.slice();
})();
""" % (json.dumps(ROSTER), json.dumps([NW, LS, GA, EE, BK, CM]), json.dumps(NW), json.dumps(LS), json.dumps(NW))


def _src():
    return io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()


class AUniqueWearsItsOwnPictureEverywhere(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertNotIn("renderErr", self.o, self.o.get("renderErr"))
        self.assertNotIn("openErr", self.o, self.o.get("openErr"))
        self.assertEqual(self.o["errors"], [])

    def _same_everywhere(self, n, url, frm):
        r = self.o["one"][n]
        self.assertEqual(r["k"], {"url": url, "from": frm}, "%s: the resolver answered %r" % (n, r["k"]))
        self.assertEqual((r["artUrl"], r["row"], r["hover"], r["table"]), (url, url, url, url),
                         "%s draws a different picture on some surface (artUrl, row, hover, console table): %r" % (n, r))
        self.assertTrue(os.path.exists(os.path.join(ROOT, url)), "%s: %s is not on disk" % (n, url))

    def test_a_unique_with_its_own_icon_draws_it_and_not_its_base(self):
        self._same_everywhere(NW, "art/mr_nightwingsveil.png", "own-icon")

    def test_a_unique_with_its_own_game_sprite_keeps_it(self):
        self._same_everywhere(LS, "art/hd_lightsabre.png", "own-sprite")

    def test_a_unique_with_neither_falls_back_to_its_base_and_says_so(self):
        self._same_everywhere(GA, "art/hd_long_war_bow.png", "base-sprite")

    def test_a_base_sprite_registered_under_the_name_is_still_called_the_base(self):
        r = self.o["one"]["Sander's Riprap"]
        self.assertEqual(r["k"], {"url": "art/hd_heavy_boots.png", "from": "base-sprite"},
                         "a base sprite registered under an item's name is said to be its own: %r" % r["k"])

    def test_a_trimmed_label_or_the_runeword_table_never_takes_a_uniques_picture(self):
        self._same_everywhere(EE, "art/mr_etherealedge.png", "own-icon")
        self._same_everywhere(BK, "art/mr_bulkathosweddingband.png", "own-icon")
        cm = self.o["one"][CM]
        # REG-2847 - its own icon is the amulet label's file (the same picture, 100 px against 50): one item, one picture
        self.assertEqual((cm["k"]["url"], cm["artUrl"], cm["row"], cm["table"]), ("art/mr_crescentmoonamulet.png",) * 4,
                         "the runeword table drew over Crescent Moon's own icon: %r" % cm)
        am = self.o["one"]["Crescent Moon (amulet)"]
        self.assertEqual(am["row"], am["hover"], "the unique's own label differs between row and hover: %r" % am)
        self.assertEqual(am["row"], cm["row"], "the unique and its own label draw two pictures: %r / %r" % (cm, am))
        self.assertIn("mr_crescentmoon", am["row"] or "", am)

    def test_a_runeword_label_wears_its_base_not_the_amulets_icon(self):
        """REG-2806 - "Crescent Moon (sword)" is the runeword, and drew the unique amulet's icon (identical bytes)."""
        self._same_everywhere("Crescent Moon (sword)", "art/hd_crystal_sword.png", "base-sprite")
        self.assertNotEqual(self.o["one"]["Crescent Moon (amulet)"]["row"], "art/hd_crystal_sword.png")

    def test_no_runeword_label_draws_an_icon_another_kind_of_item_owns(self):
        """The REG-2806 sweep as a law: group every art key by the BYTES of the picture it draws. A group may hold many
        uniques of one base family (the game draws them alike), never a runeword beside a unique or set item's icon."""
        import hashlib
        digest, groups = {}, {}
        for k, (url, kind) in self.o["kinds"].items():
            p = os.path.join(ROOT, (url or "").split("?")[0])
            if not url or not os.path.exists(p):
                continue
            if p not in digest:
                digest[p] = hashlib.md5(io.open(p, "rb").read()).hexdigest()
            groups.setdefault(digest[p], []).append((k, kind, url))
        self.assertGreater(len(groups), 300, "PREMISE: almost no art keys carry a kind: %d" % len(groups))
        mixed = [g for g in groups.values()
                 if any(kind == "runeword" for _, kind, _ in g) and any("/mr_" in u and kind != "runeword" for _, kind, u in g)]
        self.assertEqual(mixed, [], "a runeword label draws the icon of a unique or set item: %r" % mixed[:3])

    def test_the_cards_draw_the_same_picture(self):
        self.assertEqual(self.o["card"], {"nw": "art/mr_nightwingsveil.png", "ls": "art/hd_lightsabre.png"},
                         "the locker card's cells: %r" % self.o["card"])
        self.assertEqual(self.o["mule"], "art/mr_nightwingsveil.png", "the mule card's cell: %r" % self.o["mule"])

    def test_every_unique_the_table_knows_draws_its_own_picture_when_one_exists(self):
        ro = {n: r for n, r in self.o["roster"].items() if r}
        self.assertGreater(len(ro), 300, "PREMISE: the resolver knows almost no uniques: %d" % len(ro))
        bad, split, gone = [], [], []
        for n, r in ro.items():
            want = r["own"] or r["icon"]
            if want and r["url"] != want:
                bad.append((n, r["url"], want))
            if not (r["artUrl"] == r["row"] == r["url"] == r["table"]):
                split.append((n, r))
            if not os.path.exists(os.path.join(ROOT, r["url"])):
                gone.append((n, r["url"]))
        self.assertEqual(bad, [], "a unique with its own picture draws another: %r" % bad[:10])
        self.assertEqual(split, [], "a unique draws different pictures across surfaces: %r" % split[:5])
        self.assertEqual(gone, [], "a resolved picture is not on disk: %r" % gone[:10])
        falls = sorted(n for n, r in ro.items() if r["from"] == "base-sprite")
        self.assertTrue(all(not ro[n]["own"] and not ro[n]["icon"] for n in falls), falls)
        print("\n[REG-2805] uniques the resolver knows: %d - own sprite %d, own icon %d, base-sprite fallback %d: %s"
              % (len(ro), sum(1 for r in ro.values() if r["from"] == "own-sprite"),
                 sum(1 for r in ro.values() if r["from"] == "own-icon"), len(falls), ", ".join(falls)))

    def test_every_unique_draws_the_same_picture_in_its_row_and_its_hover(self):
        """C2's "rows vs hover", over the whole roster. The bare "Crescent Moon" is ALSO a Reign of the Warlock runeword:
        its hover is the runeword's card, and the vault files the unique as "Crescent Moon (amulet)" (REG-2228)."""
        split = {n: p for n, p in self.o["pair"].items() if p[0] != p[1] and n != CM}
        self.assertEqual(split, {}, "a unique's row and hover draw different pictures: %r" % split)
        self.assertGreater(sum(1 for p in self.o["pair"].values() if p[0]), 390, "PREMISE: the roster drew almost no pictures")
        # REG-2847 (v3831 second eye) - measured on the hover's own picture line: a Sunder's row and hover draw one picture
        self.assertEqual([r for r in self.o["renewed"] if r[1] != r[2] or not r[1]], [], "a Sunder's row and hover differ: %r" % self.o["renewed"])

    def test_the_row_hover_and_card_paths_all_ask_artUrl_and_artUrl_asks_the_resolver_first(self):
        s = _src()
        art_url = s[s.find("function artUrl(name){"):s.find("window._artTier = _artTier;")]
        self.assertLess(art_url.find("_keeperArt(name)"), art_url.find("var direct ="), "artUrl reads its table before the resolver")
        art_or = s[s.find("function artOr(name, fallbackHtml, size){"):s.find("function artOr(name, fallbackHtml, size){") + 1200]
        self.assertIn("var _raw = artUrl(name);", art_or, "the row path (artOr) no longer asks artUrl")
        self.assertEqual(s.count("var url = (typeof artUrl==='function') ? ((_ctx && artUrl(_ctx)) || (r.builtBase && artUrl(r.artName)) || artUrl(nm) || artUrl(r.artName)) : '';"), 1,
                         "the hover's picture line no longer asks artUrl")
        self.assertIn("function art(n, glyph, size){ glyph = glyph || '◆'; try { if (typeof artOr === 'function') { var html = artOr(n, glyph, size || 'sm');", s,
                      "the vault's art() (cards, cells, chips) no longer draws through artOr")


RED_PROOF = [
    {"why": "REG-2805 - v406 drops the unique's own icon and draws its base again",
     "file": "bible.html",
     "find": "    else if (_cur && _cur.indexOf(\"art/mr_\") === 0) _KEEPER_ART.icon[_hk] = _cur;    /* REG-2805 own icon */\n",
     "replace": "    else if (false) _KEEPER_ART.icon[_hk] = _cur;    /* REG-2805 own icon */\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2805 - the game's own sprite (v384) is not kept, so Lightsabre draws the plain Crystal Sword",
     "file": "bible.html",
     "find": "    if (_cur && _cur.indexOf(\"art/hd_\") === 0 && _cur !== _HDUS[_hk]) _KEEPER_ART.own[_hk] = _cur;   /* REG-2805 own sprite (v384) */\n",
     "replace": "    if (false) _KEEPER_ART.own[_hk] = _cur;   /* REG-2805 own sprite (v384) */\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2805 - artUrl's label rules run before the resolver (Ethereal Edge draws the runeword Edge)",
     "file": "bible.html",
     "find": "  var _kp = (typeof _keeperArt === 'function') ? _keeperArt(name) : null;\n  if (_kp) return _kp.url;\n",
     "replace": "  var _kp = null;\n  if (_kp) return _kp.url;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2805 - the runeword table draws over a keeper's own picture (Crescent Moon)",
     "file": "bible.html",
     "find": "    if ((!_rc || _rc.indexOf(\"art/hd_\") !== 0) && !_keeperArt(_rk)) D2IO_ART[_rk] = _HDRW[_rk];\n",
     "replace": "    if ((!_rc || _rc.indexOf(\"art/hd_\") !== 0)) D2IO_ART[_rk] = _HDRW[_rk];\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2805 - an icon registered without the apostrophe is not found (Bul-Kathos' Wedding Band)",
     "file": "bible.html",
     "find": "      if (_ic && _ic.indexOf(\"art/mr_\") === 0) _KEEPER_ART.icon[_hk] = _ic;\n",
     "replace": "      if (false) _KEEPER_ART.icon[_hk] = _ic;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2805 - an hd_ that is the base sprite is called the item's own (Sander's Riprap's Heavy Boots)",
     "file": "bible.html",
     "find": " && _cur !== _HDUS[_hk]) _KEEPER_ART.own[_hk] = _cur;",
     "replace": ") _KEEPER_ART.own[_hk] = _cur;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2806 - a runeword label keeps the icon it was registered with (Crescent Moon (sword) draws the amulet)",
     "file": "bible.html",
     "find": "      if (!(_rt && _rt.t === 'Runeword') || !/\\([^)]*\\)\\s*$/.test(_rl) || _keeperArt(_rl)) return;\n",
     "replace": "      if (true) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2805 - D2IO_ART keeps the base, so the console's copy draws another picture than the board",
     "file": "bible.html",
     "find": "    if (_ka) D2IO_ART[_hk] = _ka.url;                                                  /* REG-2805 one picture */\n",
     "replace": "    if (_ka) D2IO_ART[_hk] = _HDUS[_hk];                                                  /* REG-2805 one picture */\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
