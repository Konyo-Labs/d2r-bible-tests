# -*- coding: utf-8 -*-
"""REG-2903, REG-2904, REG-2905 - AN ITEM WHOSE BASE THE NAME DOES NOT GIVE IS UNKNOWN EVERYWHERE, AND ITS MARK ASKS WHY.

The house rule (his MAGIC & RARE, 2026-10-28): an item whose base cannot be established from its own name or record shows
UNKNOWN everywhere - the card, the mule window, FIND and the hover alike, one logic, never a guess on one surface and the
mark on another; and a doubt becomes a question ("ring or jewel? the name does not say; a tooltip look settles it").
Measured on the whole page in node (tv/vault_page_node.py) before the fix, with the ALT's Raven Whorl shape (a TV-read rare
whose suffix is a ring's or a jewel's):
  * Raven Whorl drew the mark in the mule window and in FIND, ring1_graphic on the card (its cell fell back to the keyword
    sprite) - and the mark said nothing about why;
  * a kept rare with no base (Chaos Whorl, Havoc Eye Ring) drew the mark on the card, in the window and in FIND, and the
    keyword sprite in the hover and in the registered list's Magic & Rare rows; a throw-out read (Bone Gyre) hovered as a ring.
Now one answer decides every surface (_artRolledBase, asked by artOr and by the hover): a base from the record, the
catalogue row or the rolled-name grammar draws its picture everywhere; with none, every surface shows the mark, the mark
carries the question as its tooltip, the hover card says it, and no keyword sprite stands in (REG-2903). The card's record
cells (REG-2904) and the registered list's Magic & Rare rows (REG-2905) draw artOr's answer, not their own fallback.
RED_PROOF below.
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

RJ = "ring or jewel? the name does not say; a tooltip look settles it"
WB = "which base? the name does not say; a tooltip look settles it"
# the items in doubt, each with the question its mark carries
DOUBT = {"Raven Gyre": RJ,             # a TV-read rare the grammar routes to MAGIC & RARE: a record on the locker
         "Chaos Gyre": RJ,             # a keeper kept with no base
         "Havoc Eye Ring": WB}          # a keeper no rule reads
CONTROL = {"Doom Eye": "Jewel"}         # a TV-read rare whose suffix names one slot: its base everywhere
READ = ("Bone Gyre", RJ)                # a throw-out read in doubt (the review's hover)
KEEPERS = {"Chaos Gyre": {"q": "rare", "base": ""}, "Havoc Eye Ring": {"q": "rare", "base": ""}}
STUBS = ["Raven Gyre", "Doom Eye"]
STUB = lambda n: {"rarity": "basic", "base": n, "cat": "TV-vaulted", "val": "tv", "desc": "fixture"}  # noqa: E731
PRELUDE = "localStorage.setItem('d2r_ownerClaim', '*');\n" + "".join(
    "localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(json.dumps(v)))
    for k, v in (("d2r_magicFinds", KEEPERS), ("d2r_tvExtraItems", {n: STUB(n) for n in STUBS}), ("d2r_owned", STUBS),
                 ("d2r_unknownReads", [READ[0]])))

BODY = r"""
(function(){
var W = window, MR = 'magic-rare', NAMES = %s, READ = %s;
function pic(html, at){
  if (at < 0) return 'no tile';
  var seg = html.slice(at, at + 2500), s = seg.search(/ src="/), f = seg.search(/class="[^"]*d2art-failed"/);
  if (f >= 0 && (s < 0 || f < s)) { var t = /class="[^"]*d2art-failed"[^>]*?title="([^"]*)"/.exec(seg.slice(f)); return 'MARK' + (t ? ':' + t[1] : ''); }
  var m = / src="([^"]+)"/.exec(seg);
  return m ? m[1].split('?')[0] : 'no img';
}
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); }
H.flush(60, 3);
OUT.span = W._vaultRecordsForMule(MR);
var shelf = String((document.getElementById('vault-shelf') || {}).innerHTML || '');
var at = shelf.indexOf('data-vault-mule="' + MR + '"'), nx = at < 0 ? -1 : shelf.indexOf('data-vault-mule="', at + 10);
var card = at < 0 ? '' : shelf.slice(at, nx < 0 ? shelf.length : nx);
var reg = String((document.getElementById('vault-registered') || {}).innerHTML || '');
try { W.openMuleCard(MR); } catch (e) { OUT.openErr = String(e && e.message || e); }
H.flush(60, 3);
var det = String((document.getElementById('vault-detail') || {}).innerHTML || '');
function hover(n){
  var r = W._arttipResolve(n) || {}, row = /src="([^"]+)"/.exec(W.artOr(n, '', 'sm') || '');
  /* the name hover's picture, in the shipped order (artUrl(nm) || artUrl(artName), artOr's picture, then artSrc), and the
     picture hover's (artUrl of the name, its artName, its clean name, then artSrc - the mark holds no img) */
  var name = W.artUrl(n) || (r.artName ? W.artUrl(r.artName) : null) || (row ? row[1] : null) || r.artSrc || 'none';
  var art = W.artUrl(n) || (r.artName ? W.artUrl(r.artName) : null) || W.artUrl(W._artSlotClean(n)) || r.artSrc || 'none';
  return { name: String(name).split('?')[0], art: String(art).split('?')[0], desc: String(r.desc || '') };
}
OUT.s = {};
NAMES.forEach(function(n){
  W.vaultFind(n); H.flush(60, 3);
  var fr = String((document.getElementById('vault-find-results') || {}).innerHTML || '');
  var cAt = card.indexOf('data-vault-item="' + n + '"'); if (cAt < 0) cAt = card.indexOf('data-magic-find="' + n + '"');
  var rAt = reg.indexOf('data-magic-find="' + n + '"');
  OUT.s[n] = { card: pic(card, cAt), win: pic(det, det.indexOf('title="' + n + ' (')), find: pic(fr, fr.indexOf('vfr-')),
               reg: rAt < 0 ? 'not listed' : pic(reg, rAt), hover: hover(n), answer: W._artRolledBase(n) };
});
OUT.read = { hover: hover(READ), answer: W._artRolledBase(READ) };
OUT.jewel = W.artUrl('Jewel');
OUT.errors = H.errors.slice();
})();
""" % (json.dumps(sorted(list(DOUBT) + list(CONTROL))), json.dumps(READ[0]))


class ABaseInDoubtIsUnknownEverywhere(unittest.TestCase):

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
        # REG-2971 (#202 P3b): every keeper is a record now, homed on MAGIC & RARE by the keeper rule
        self.assertEqual(sorted(self.o["span"] or {}), sorted(STUBS + list(KEEPERS)), "PREMISE: the two stubs and the keepers are not the locker's records: %r" % self.o["span"])

    def test_one_answer_says_the_doubt(self):
        for n, ask in DOUBT.items():
            self.assertEqual(self.o["s"][n]["answer"], {"base": "", "ask": ask}, n)
        self.assertEqual(self.o["s"]["Doom Eye"]["answer"], {"base": "Jewel", "ask": None})
        self.assertEqual(self.o["read"]["answer"], {"base": "", "ask": READ[1]})

    def test_a_base_in_doubt_is_the_mark_on_every_tile_and_the_mark_asks_why(self):
        bad = {}
        for n, ask in DOUBT.items():
            s = self.o["s"][n]
            tiles = {k: s[k] for k in ("card", "win", "find")}
            if n != "Raven Gyre":
                tiles["reg"] = s["reg"]                 # a record, not a keeper: the registered list's other columns draw no picture
            wrong = {k: v for k, v in tiles.items() if v != "MARK:" + ask}
            if wrong:
                bad[n] = wrong
        self.assertEqual(bad, {}, "a tile of an item in doubt draws a picture, or its mark does not ask why: %r" % bad)

    def test_the_hover_draws_no_guess_and_asks_the_question(self):
        bad = {}
        for n, ask in list(DOUBT.items()) + [(READ[0], READ[1])]:
            h = self.o["read"]["hover"] if n == READ[0] else self.o["s"][n]["hover"]
            if h["name"] != "none" or h["art"] != "none" or ask not in h["desc"]:
                bad[n] = h
        self.assertEqual(bad, {}, "the hover of an item in doubt draws a guessed picture, or does not ask: %r" % bad)

    def test_a_base_the_name_gives_draws_its_picture_everywhere(self):
        s = self.o["s"]["Doom Eye"]
        got = {k: s[k] for k in ("card", "win", "find")}
        got["hover"] = s["hover"]["name"]
        self.assertEqual(got, {k: self.o["jewel"] for k in got}, "Doom Eye (a jewel by its name) draws: %r" % got)
        self.assertNotIn("the name does not say", s["hover"]["desc"])


RED_PROOF = [
    {"why": "REG-2903 - the mark of an item in doubt says nothing again",
     "file": "bible.html",
     "find": "${_ask ? ` title=\"${_d2artEsc(_ask)}\" data-art-ask=\"1\"` : ''}",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2903 - a two-slot rare is not asked (no question, its hover falls back to the keyword ring)",
     "file": "bible.html",
     "find": "    out.ask = rq.slots.join(' or ').toLowerCase() + '? the name does not say; a tooltip look settles it';   /* REG-2903 the doubt asked */\n",
     "replace": "    out.ask = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2903 - a kept item no rule reads is not asked",
     "file": "bible.html",
     "find": "  else if (rolled) out.ask = 'which base? the name does not say; a tooltip look settles it';\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2903 - the keeper's hover draws the keyword sprite over the doubt again",
     "file": "bible.html",
     "find": "artSrc: (!_abq && typeof _magicArtSrc === 'function') ? _magicArtSrc(_mfb || nm) : null,",
     "replace": "artSrc: (typeof _magicArtSrc === 'function') ? _magicArtSrc(_mfb || nm) : null,",
     "matches": 1, "needs": "node"},
    {"why": "REG-2903 - a throw-out read in doubt hovers as a ring again",
     "file": "bible.html",
     "find": "|| (!_abT && typeof _magicArtSrc === 'function' ? _magicArtSrc(_tc) : '') || null;",
     "replace": "|| (typeof _magicArtSrc === 'function' ? _magicArtSrc(_tc) : '') || null;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2903 - the hover card does not say the question",
     "file": "bible.html",
     "find": "return { artName: nm, desc: _extraTipHtml(nm) + _askH, rich: true };",
     "replace": "return { artName: nm, desc: _extraTipHtml(nm), rich: true };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2904 - the card's record cell falls back to the keyword sprite again (Raven Whorl a ring on the card only)",
     "file": "bible.html",
     "find": "          + '<span class=\"vm-cell-art\">' + _cellArt + '</span>' + osTag + _cntTag   /* REG-2904 one answer */\n",
     "replace": "          + '<span class=\"vm-cell-art\">' + ((/ src=\"/.test(_cellArt) || typeof _magicArtSrc!=='function' || !_magicArtSrc(n)) ? _cellArt : '<span class=\"d2art-wrap lg\" role=\"img\" aria-label=\"'+esc(n)+'\"><img class=\"d2art-img\" src=\"'+_magicArtSrc(n)+'\" alt=\"\" loading=\"lazy\"></span>') + '</span>' + osTag + _cntTag\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2905 - the registered list's Magic & Rare rows draw the keyword sprite again",
     "file": "bible.html",
     "find": "        var _icon=art(n, '\\u25c6', 'sm');   /* REG-2905 one answer */\n",
     "replace": "        var _src=(typeof _magicArtSrc==='function')?_magicArtSrc(_mfBase(n)||n):null, _icon=_src?'<span class=\"d2art-wrap sm\" role=\"img\" aria-label=\"'+esc(n)+'\"><img class=\"d2art-img\" src=\"'+_src+'\" alt=\"\" loading=\"lazy\"></span>':'<span class=\"vrg-mdot\" style=\"background:'+col+'\"></span>';\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
