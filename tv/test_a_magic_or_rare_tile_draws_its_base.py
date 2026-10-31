# -*- coding: utf-8 -*-
"""REG-2851, REG-2852 - A MAGIC OR RARE ITEM DRAWS ITS BASE'S PICTURE, THE SAME ON THE CARD, THE WINDOW, FIND AND THE HOVER.

His report, 2026-10-28 19:31 (the ALT's shadow on v3829): MAGIC & RARE drew several items as a white diamond with a dashed
border - "the images are not rendering proeprly some bug here". Measured on the whole page in node (tv/vault_page_node.py)
with the shapes his locker holds:
  * REG-2851 - artOr drew a rolled item as the base its record names, and nothing when none is named: the throw-out
    review's keep writes base '', a legacy record is a bare quality string, and a TV stub's base is its own name. So
    "Grim Spiral (rare)", "Bitter Noose", "Rune Eye" and the stub "Doom Eye" drew the mark on the card, in the window and in
    FIND. _rolledQuality is the board's one grammar for a rolled name (REG-2054, what the router files them by): a magic
    charm / jewel / ring / amulet carries its base in its name, and a rare's suffix word belongs to one slot or to several.
    artOr now reads the base off that grammar when nothing recorded one; two slots (Whorl: a ring or a jewel) stay UNKNOWN
    and keep the mark. Swept: the card's record cells asked artUrl alone and fell to the keyword sprite, so a stub the
    window drew as hd_ring the card drew as ring1_graphic - they ask artOr's picture first now (the hover already did).
  * REG-2852 - a rare kept with its base on record still drew the mark when the base itself was no art key: 36 of
    BASE_DB's 508 bases answered no picture (a rare Plated Belt). A base with no picture now wears the one sprite the v406
    table gives every unique built on it (Bladebuckle and Sigon's Wrap, Plated Belts: hd_girdle_h) - additive, and a base
    whose uniques disagree, or that no unique is built on, stays UNKNOWN. Swept with it (GrokBot's ACT-2): one sprite per
    charm size - a TV-read charm wore v305's keyword graphic (bluecharm_graphic) while a keeper with its base on record
    wore hd_charm_small, and a Large Charm wore the grand one; each now wears its size's base sprite.
RED_PROOF below.
"""
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

KEEPERS = {
    "Grim Spiral (rare)": {"q": "rare", "base": ""},          # the throw-out review's keep
    "Bitter Noose": "rare",                                  # a legacy record
    "Rune Eye": {"q": "rare", "base": ""},
    "Chaos Gyre": {"q": "rare", "base": ""},                  # Gyre: a ring or a jewel - UNKNOWN (v3849: a Whorl is a ring by his ruling)
    "Stone Knot": {"q": "rare", "base": "Ring", "mods": []},
    "Fine Small Charm of Vita": {"q": "magic", "base": "Small Charm", "mods": [], "border": True},   # a charm: its sprite only
    "Ruby Amulet of Balance": {"q": "magic", "base": "Amulet", "mods": [], "border": True},
    "Bone Clasp": {"q": "rare", "base": "Plated Belt", "mods": []},
}
STUBS = ["Doom Eye", "Grim Knot"]            # TV stubs the grammar routes to MAGIC & RARE: the locker's records
OWNED = ["Stone Knot", "Bone Clasp"] + STUBS
# the base each one's picture is, on MAGIC & RARE's card and window, FIND and the hover. MAGIC & RARE holds no charms (his
# 2026-10-28 ruling, REG-2895), so the magic keeper with its base on record is an amulet; the charm keeper stays in KEEPERS
# for the one-sprite-per-size law below.
BASE = {"Grim Spiral (rare)": "Ring", "Bitter Noose": "Amulet", "Rune Eye": "Jewel", "Doom Eye": "Jewel", "Grim Knot": "Ring",
        "Stone Knot": "Ring", "Ruby Amulet of Balance": "Amulet", "Bone Clasp": "Plated Belt"}
UNKNOWN = "Chaos Gyre"
# one sprite per charm size, whichever store the charm comes from: (name, its size's base)
CHARMS = [("Fine Small Charm of Vita", "Small Charm"), ("Small Charm of Balance", "Small Charm"),
          ("Serpent's Large Charm of Vita", "Large Charm"), ("Lion Branded Grand Charm", "Grand Charm"),
          ("Sharp Grand Charm of Sustenance", "Grand Charm")]
TVX = {n: None for n in STUBS + ["Small Charm of Balance", "Serpent's Large Charm of Vita", "Lion Branded Grand Charm"]}
STUB = lambda n: {"rarity": "basic", "base": n, "cat": "TV-vaulted", "val": "tv", "desc": "fixture"}  # noqa: E731

PRELUDE = "localStorage.setItem('d2r_ownerClaim', '*');\n" + "".join(
    "localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(json.dumps(v)))
    for k, v in (("d2r_magicFinds", dict(KEEPERS, **{"Sharp Grand Charm of Sustenance": {"q": "magic", "base": "Grand Charm", "mods": []}})),
                 ("d2r_tvExtraItems", {n: STUB(n) for n in TVX}), ("d2r_owned", OWNED)))

BODY = r"""
(function(){
var W = window, MR = 'magic-rare', NAMES = %s;
function pic(html, at){
  if (at < 0) return 'no tile';
  var seg = html.slice(at, at + 2500), s = seg.search(/ src="/), f = seg.search(/class="[^"]*d2art-failed"/);
  if (f >= 0 && (s < 0 || f < s)) return 'MARK';
  var m = / src="([^"]+)"/.exec(seg);
  return m ? m[1].split('?')[0] : 'no img';
}
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); }
H.flush(60, 3);
OUT.span = W._vaultRecordsForMule(MR);
var shelf = String((document.getElementById('vault-shelf') || {}).innerHTML || '');
var at = shelf.indexOf('data-vault-mule="' + MR + '"'), nx = at < 0 ? -1 : shelf.indexOf('data-vault-mule="', at + 10);
var card = at < 0 ? '' : shelf.slice(at, nx < 0 ? shelf.length : nx);
try { W.openMuleCard(MR); } catch (e) { OUT.openErr = String(e && e.message || e); }
H.flush(60, 3);
var det = String((document.getElementById('vault-detail') || {}).innerHTML || '');
OUT.s = {};
NAMES.forEach(function(n){
  var r = W._arttipResolve(n), row = /src="([^"]+)"/.exec(W.artOr(n, '', 'sm') || '');
  /* the name hover's picture, in the shipped order (artUrl(nm) || artUrl(artName), then artOr's picture, then artSrc -
     tv/test_the_art_resolver_folds_the_apostrophe.py pins that order in the source) */
  var hover = W.artUrl(n) || (r && r.artName ? W.artUrl(r.artName) : null) || (row ? row[1] : null) || (r && r.artSrc) || 'none';
  W.vaultFind(n); H.flush(60, 3);
  var fr = String((document.getElementById('vault-find-results') || {}).innerHTML || '');
  OUT.s[n] = { card: pic(card, card.indexOf('data-arttip="' + n + '"')), win: pic(det, det.indexOf('title="' + n + ' (')),
               find: pic(fr, fr.indexOf('vfr-')), hover: String(hover).split('?')[0] };
});
OUT.base = {};
%s.concat(['Small Charm', 'Large Charm', 'Grand Charm']).forEach(function(b){ OUT.base[b] = W.artUrl(b); });
OUT.charm = {};
%s.forEach(function(c){ var m = / src="([^"]+)"/.exec(W.artOr(c[0], '', 'sm') || ''); OUT.charm[c[0]] = m ? m[1].split('?')[0] : 'MARK'; });
/* REG-2852: every base, what it draws, and the sprites the v406 table gives the uniques built on it */
OUT.bases = {};
var by = {};
Object.keys(_KEEPER_ART.base).forEach(function(u){
  var c = (typeof ITEM_CODEX !== 'undefined' && ITEM_CODEX[u]) || null, t = (typeof ITEM_TIP !== 'undefined' && ITEM_TIP[u]) || null;
  var b = (c && c.base) || (t && t.b) || '';
  if (b && Object.prototype.hasOwnProperty.call(BASE_DB, b)) (by[b] = by[b] || {})[_KEEPER_ART.base[u]] = 1;
});
Object.keys(BASE_DB).forEach(function(b){ OUT.bases[b] = [W.artUrl(b), Object.keys(by[b] || {}), D2IO_ART[b] || null]; });
OUT.errors = H.errors.slice();
})();
""" % (json.dumps(sorted(set(BASE) | {UNKNOWN})), json.dumps(sorted(set(BASE.values()))), json.dumps(CHARMS))


class AMagicOrRareTileDrawsItsBase(unittest.TestCase):

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
        self.assertEqual(sorted(self.o["span"] or {}), sorted(STUBS), "PREMISE: the stubs are not the locker's records: %r" % self.o["span"])

    def test_every_base_named_here_has_a_picture_on_disk(self):
        for b, u in self.o["base"].items():
            self.assertTrue(u, "PREMISE: %s has no picture at all" % b)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, u.split("?")[0])), "%s: %s is not on disk" % (b, u))

    def test_no_surface_draws_the_mark_for_an_item_whose_base_has_art(self):
        marks = {n: {k: v for k, v in s.items() if v in ("MARK", "no tile", "no img", "none")}
                 for n, s in self.o["s"].items() if n != UNKNOWN}
        marks = {n: m for n, m in marks.items() if m}
        self.assertEqual(marks, {}, "these draw the missing-art mark (or no tile) where their base has a picture: %r" % marks)

    def test_each_draws_its_base_picture_on_every_surface(self):
        wrong = {}
        for n, b in BASE.items():
            want = self.o["base"][b]
            got = self.o["s"][n]
            if any(v != want for v in got.values()):
                wrong[n] = (b, want, got)
        self.assertEqual(wrong, {}, "an item draws another picture than its base's (base, its picture, card/win/find/hover): %r" % wrong)

    def test_a_name_that_says_two_slots_stays_unknown(self):
        s = self.o["s"][UNKNOWN]
        self.assertEqual((s["win"], s["find"]), ("MARK", "MARK"),
                         "a Gyre (a ring or a jewel) was given a base picture - a guess drawn as a fact: %r" % s)

    def test_one_sprite_per_charm_size(self):
        got = {n: self.o["charm"][n] for n, _ in CHARMS}
        want = {n: self.o["base"][b] for n, b in CHARMS}
        self.assertEqual(got, want, "a charm wears another sprite than its size's (got, want): %r" % ({n: (got[n], want[n]) for n in got if got[n] != want[n]},))

    def test_a_base_with_no_picture_wears_its_uniques_one_sprite(self):
        bases = self.o["bases"]
        self.assertEqual(bases["Plated Belt"][0], "art/hd_girdle_h.png", "a Plated Belt draws %r" % (bases["Plated Belt"],))
        # every base the v406 table settles (one sprite, its uniques agree) draws a picture now
        open_ = sorted(b for b, (u, sprites, _) in bases.items() if not u and len(sprites) == 1 and sprites[0].startswith("art/hd_"))
        self.assertEqual(open_, [], "these bases have one sprite in the v406 table and still draw nothing: %r" % open_)
        # additive: a base that had a key keeps it (Belt's own graphic, not the v406 Mesh-family sprite)
        self.assertEqual(bases["Belt"][0], "art/belt_graphic.png", "the fill overwrote a base's own picture: %r" % (bases["Belt"],))
        # what stays UNKNOWN is what the table cannot settle
        left = sorted(b for b, (u, sprites, _) in bases.items() if not u)
        self.assertTrue(all(len(bases[b][1]) != 1 for b in left), "a base left blank has one sprite to wear: %r" % left)
        missing = [u for b, (u, _, _) in bases.items() if u and u.startswith("art/hd_") and not os.path.isfile(os.path.join(ROOT, u))]
        self.assertEqual(missing, [], "a base picture is not on disk: %r" % missing)


RED_PROOF = [
    {"why": "REG-2851 - artOr reads no base off the one grammar again (Grim Spiral, Bitter Noose, Rune Eye, Doom Eye draw the mark)",
     "file": "bible.html",
     "find": "  try { rq = (typeof _rolledQuality === 'function') ? _rolledQuality(clean) : null; } catch (eRq) { rq = null; }\n",
     "replace": "  rq = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2851 - a rare's suffix that names one slot is not read as its base (Grim Spiral, Doom Eye draw the mark)",
     "file": "bible.html",
     "find": "  if (rq && rq.q === 'rare' && rq.slots && rq.slots.length === 1) { out.base = String(rq.slots[0]); return out; }   /* REG-2851 one grammar */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2851 - a two-slot rare is guessed as its first slot (a Whorl drawn as a ring, a guess as a fact)",
     "file": "bible.html",
     "find": "rq.slots && rq.slots.length === 1) { out.base",
     "replace": "rq.slots && rq.slots.length >= 1) { out.base",
     "matches": 1, "needs": "node"},
    {"why": "REG-2851 - the card's record cell asks artUrl alone again (Grim Knot: ring1_graphic on the card, hd_ring elsewhere)",
     "file": "bible.html",
     "find": "          + '<span class=\"vm-cell-art\">' + _cellArt + '</span>' + osTag + _cntTag   /* REG-2904 one answer */\n",
     "replace": "          + '<span class=\"vm-cell-art\">' + (((typeof artUrl==='function'&&artUrl(n)) || typeof _magicArtSrc!=='function' || !_magicArtSrc(n)) ? _cellArt : '<span class=\"d2art-wrap lg\" role=\"img\" aria-label=\"'+esc(n)+'\"><img class=\"d2art-img\" src=\"'+_magicArtSrc(n)+'\" alt=\"\" loading=\"lazy\"></span>') + '</span>' + osTag + _cntTag\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2852 - a TV-read small charm wears the keyword graphic again (bluecharm beside hd_charm_small)",
     "file": "bible.html",
     "find": "largecharm:'art/hd_charm_medium.png', smallcharm:'art/hd_charm_small.png',   /* REG-2852 one sprite per charm size */",
     "replace": "largecharm:'art/hd_charm_medium.png', smallcharm:'art/bluecharm_graphic.png',",
     "matches": 1, "needs": "node"},
    {"why": "REG-2852 - a Large Charm wears the grand charm's sprite again (no 'large charm' rule)",
     "file": "bible.html",
     "find": "['large charm','largecharm'], ",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2852 - a base with no art key draws nothing again (a rare Plated Belt draws the mark)",
     "file": "bible.html",
     "find": "      if (_bs.length === 1 && _bs[0].indexOf(\"art/hd_\") === 0 && !artUrl(_bb)) D2IO_ART[_bb] = _bs[0];   /* REG-2852 base sprite */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2852 - the fill overwrites a base's own picture (Belt loses belt_graphic)",
     "file": "bible.html",
     "find": "_bs[0].indexOf(\"art/hd_\") === 0 && !artUrl(_bb)) D2IO_ART[_bb]",
     "replace": "_bs[0].indexOf(\"art/hd_\") === 0) D2IO_ART[_bb]",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
