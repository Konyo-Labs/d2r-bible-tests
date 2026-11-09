# -*- coding: utf-8 -*-
"""#97 (his 11-06: "when price checking an item it should also pull up a image of that item from the local database and
have an image with the mods ... on the left normal tier with a random shako image and its mods that it can range from
minimum to maximum. and the right side an image of PERFECT shako with perfected mods ... in the same format and structure
and theme") - THE PRICE CHECK DRAWS A NORMAL AND A PERFECT CARD.

Under the price line: the item's picture (artUrl) over the game's own box (d2Tip - the Character Builder's ADD ITEM look),
NORMAL with every untouched roll as its range, PERFECT with every ranged roll and the defense at the top of its range, each
with its tier's stored price. The item is the one the console's d2jspResolveItem names ("shako" is Harlequin Crest); a name
that is not one item says so in a line. The page half runs in node on the whole page (tv/vault_page_node); the console half
runs the quote block's resolver in node. RED_PROOF below.

v3884 (#130, his 11-08 ~10:25: "the engima for price check should be rendering the image on the left of a normal tier
engima and its price ... like it is for shako" and "i want emphasis on the prices and different color so its seen. more
title based ... colors and emphasizing the title based on the color unique/set/runeword ... the image itself HD art ...
next to the keyword ... image cursor floating when hovering it all the details and mods"): a RUNEWORD draws its two cards
(the shared resolver knows uniques and set pieces; the item database's entry knows the runeword); each tier's price is a
titled block; the item's title rides above both cards in its rarity's colour with its HD art, and that art opens the
board's own hover card (the mule window's d2Tip lane).
"""
import io
import json
import os
import re
import shutil
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

PAGE = r"""
var db = { normal: { fg: 45, n: 8, low: 15, high: 75 }, perfect: { fg: null, n: 0 } };
OUT.shako = window._d2jspTierCardsHtml('Harlequin Crest', db);
OUT.arach = window._d2jspTierCardsHtml('Arachnid Mesh', db);
OUT.base = window._d2jspTierCardsHtml('shako', db);
OUT.nodb = window._d2jspTierCardsHtml('Arachnid Mesh', { unknown: 'the price DB at this console would not read' });
OUT.enigma = window._d2jspTierCardsHtml('Enigma', { normal: { fg: 1500, n: 4, nEff: 4, conf: 0.3 }, perfect: { fg: 2000, n: 1, nEff: 1, conf: 0.1 } });
"""


def _plain(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def _card(html, kind):
    m = re.search(r'<figure class="d2jsp-tier d2jsp-tier-%s"[^>]*>(.*?)</figure>' % kind, html or "", re.S)
    return m.group(1) if m else None


@unittest.skipIf(VPN.NODE is None, "node is absent - this law is UNMEASURED here, not passing")
class ThePriceCheckDrawsTwoCards(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(PAGE, timeout=600)

    def test_each_card_is_the_items_picture_over_the_games_box_with_its_price(self):
        for kind, price in (("normal", "Normal price 45 fg"), ("perfect", "Perfect price")):
            c = _card(self.o["shako"], kind)
            self.assertIsNotNone(c, "no %s card for Harlequin Crest: %r" % (kind, (self.o["shako"] or "")[:300]))
            self.assertIn('src="art/mr_harlequincrestshako.png"', c, "the %s card has no picture of the item" % kind)
            self.assertIn('class="d2tip d2jsp-tier-box"', c, "the %s card is not the game's box (d2Tip)" % kind)
            self.assertIn("Harlequin Crest", _plain(c))
            self.assertIn(price, _plain(c), "the %s card does not carry its tier's price" % kind)
            self.assertNotIn("strength / dexterity", _plain(c), "a character's note rides a price card")

    def test_normal_reads_each_range_and_perfect_each_top(self):
        n, p = _plain(_card(self.o["arach"], "normal")), _plain(_card(self.o["arach"], "perfect"))
        self.assertIn("90-120% Enhanced Defense", n, "NORMAL does not say the roll's range: %r" % n[:300])
        self.assertIn("+120% Enhanced Defense", p, "PERFECT is not every roll at its top: %r" % p[:300])
        self.assertNotIn("90-120%", p)
        sn, sp = _plain(_card(self.o["shako"], "normal")), _plain(_card(self.o["shako"], "perfect"))
        self.assertIn("98-141", sn, "NORMAL lost the defense range")
        self.assertRegex(sp, r"Defense: 141\b", "PERFECT's defense is not the top of its range: %r" % sp[:200])
        self.assertNotIn("98-141", sp)

    def test_a_name_that_is_not_one_item_says_so(self):
        self.assertIn('data-d2jsp-tiers="none"', self.o["base"])
        self.assertIn("is not one unique, set piece or runeword", _plain(self.o["base"]))
        self.assertNotIn("<figure", self.o["base"], "a base drew item cards")

    def test_an_unread_price_db_is_unknown_never_a_price(self):
        t = _plain(self.o["nodb"])
        self.assertIn("did not answer (UNKNOWN)", t)
        self.assertNotIn(" fg", t)

    def test_a_runeword_draws_its_two_cards(self):
        """* v3884 (#130) THE POINT - Enigma read "No item card - Enigma is not one unique, set piece or runeword" """
        n, p = _card(self.o["enigma"], "normal"), _card(self.o["enigma"], "perfect")
        self.assertIsNotNone(n, "no NORMAL card for the Enigma runeword: %r" % (self.o["enigma"] or "")[:300])
        self.assertIsNotNone(p, "no PERFECT card for the Enigma runeword")
        self.assertIn("750-775 Defense", _plain(n), "NORMAL does not say Enigma's defense range")
        self.assertIn("+775 Defense", _plain(p), "PERFECT is not Enigma at its top")
        self.assertIn('src="art/hd_plate_mail.png"', n, "the runeword card has no picture")
        self.assertIn("1500", _plain(n))
        self.assertIn("2000", _plain(p))

    def test_each_price_is_a_titled_block_in_its_own_colour(self):
        """v3884 (#130) - "emphasis on the prices and different color so its seen. more title based and structure" """
        c = _card(self.o["shako"], "normal")
        self.assertIn('<span class="d2jsp-tp-h">Normal price</span><span class="d2jsp-tp-v">45 <span class="d2jsp-tp-u">fg</span></span>', c)
        self.assertIn('<span class="d2jsp-tp-v d2jsp-tp-unk">unknown</span>', _card(self.o["shako"], "perfect"),
                      "an unpriced tier painted a price")
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            css = fh.read()
        self.assertIn(".d2jsp-tp-v{font-family:var(--serif-display,serif);font-size:var(--fs-display);font-weight:var(--fw-bold);", css,
                      "the price is no longer the card's largest figure")

    def test_the_title_wears_its_kind_and_its_art_opens_the_boards_card(self):
        """v3884 (#130) - the item's title in its rarity's colour, its HD art beside it, the board's hover card on the art"""
        self.assertIn('<div class="d2jsp-item-h d2jsp-q-runeword" data-d2jsp-item="Enigma"><span class="d2art-wrap d2jsp-iart sm" aria-label="Enigma">',
                      self.o["enigma"])
        self.assertIn('<div class="d2jsp-item-h d2jsp-q-unique" data-d2jsp-item="Harlequin Crest">', self.o["shako"])
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn(",#d2jsp-card .d2art-wrap.d2jsp-iart[aria-label]';\n  window.D2TIP_SEL = SEL;", src,
                      "the D2JSP art is outside the board's hover-card lane - no box with the mods when he hovers it")

    def test_the_search_draws_them_for_the_item_the_console_resolved(self):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        # v3889 (#178) - the cards now carry their tier's posts (a third argument) and are painted from _cards
        self.assertIn("var _cards = d2jspTierCardsHtml((j && typeof j.resolved === 'string' && j.resolved) || parsed.item, j && j.db,", src,
                      "the price search never draws the two cards, or not for the item the console resolved")
        self.assertIn("+ (_split ? d2jspEvidenceHtml(_evSim, j, { headOnly: true }) : '') + _cards", src, "the cards are drawn and never painted")


class TheConsoleNamesTheItem(unittest.TestCase):

    def test_trader_text_resolves_to_its_item(self):
        if not shutil.which("node"):
            self.skipTest("node is absent - the quote block's resolver is UNMEASURED here")
        import d2jsp_chrome as C
        self.assertEqual(C._resolved_name("shako"), "Harlequin Crest", "the console does not say which item 'shako' is")
        self.assertEqual(C._resolved_name("Harlequin Crest"), "Harlequin Crest")

    def test_the_quote_carries_it(self):
        import d2jsp_chrome as C

        class R(object):
            def __init__(self, out):
                self.returncode, self.stdout, self.stderr = 0, out, ""

        def node_run(prog, page):
            tail = prog.split("process.stdout.write")[-1]
            if "d2jspResolveItem(" in tail:
                return R("Harlequin Crest")
            if "d2jspSearchWords(" in tail:
                return R("shako")
            return R(json.dumps({"reason": "no prices", "n": 0}))
        code, out = C.d2jsp_quote("shako", "http://127.0.0.1:17772", "127.0.0.1:17772", 17772,
                                  cookie_get=lambda: ("member_id=SECRET", "ok"),
                                  transport=lambda *a: (200, {}, b"<html>Search Results</html>"), node_run=node_run,
                                  chrome_fetch=False, sec_fetch_site="same-origin")
        self.assertEqual(out.get("resolved"), "Harlequin Crest", "the quote does not say which item it priced: %r" % out)
        self.assertNotIn("SECRET", json.dumps(out))


RED_PROOF = [
    {"why": "v3884 (#130) - a runeword draws no card again ('Enigma is not one unique, set piece or runeword')",
     "file": "bible.html",
     "find": "      try { var _rw = window._mtEntryFor(name); if (_rw && _rw.q === 'r' && _rw.name) nm = _rw.name; } catch (eR) { nm = null; }\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "v3884 (#130) - the tier's price is one grey sentence again, not a titled block",
     "file": "bible.html",
     "find": "      + card('normal', 'Normal \\u00b7 every mod in its range', normal, ok ? d2jspTierPriceHtml('Normal', db.normal) : unkTier('Normal'))\n",
     "replace": "      + card('normal', 'Normal \\u00b7 every mod in its range', normal, ok ? d2jspTierSay('Normal', db.normal) : unkTier('Normal'))\n",
     "matches": 1, "needs": "node"},
    {"why": "v3884 (#130) - the item's title loses its rarity colour",
     "file": "bible.html",
     "find": "    return '<div class=\"d2jsp-item-h' + (kind ? ' d2jsp-q-' + kind : '') + '\" data-d2jsp-item=\"' + esc(nm) + '\">'",
     "replace": "    return '<div class=\"d2jsp-item-h\" data-d2jsp-item=\"' + esc(nm) + '\">'", "matches": 1, "needs": "node"},
    {"why": "v3884 (#130) - the D2JSP art leaves the board's hover-card lane (no box with the mods on hover)",
     "file": "bible.html",
     "find": ",#d2jsp-card .d2art-wrap.d2jsp-iart[aria-label]';\n  window.D2TIP_SEL = SEL;", "replace": "';\n  window.D2TIP_SEL = SEL;", "matches": 1},
    {"why": "#97 - the price search never draws the NORMAL / PERFECT cards",
     "file": "bible.html",
     "find": "        + (_split ? d2jspEvidenceHtml(_evSim, j, { headOnly: true }) : '') + _cards\n",
     "replace": "        + (_split ? d2jspEvidenceHtml(_evSim, j, { headOnly: true }) : '')\n",
     "matches": 1, "needs": "node"},
    {"why": "#97 - PERFECT is drawn with the ranges (the top-rolls option is ignored)",
     "file": "bible.html",
     "find": "        if (opts && opts.top && typeof window._cbTopRolls === 'function') e.rolls = window._cbTopRolls(it[6]);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#97 - a perfect item's defense keeps its whole range",
     "file": "bible.html",
     "find": "        if (opts && opts.top && Array.isArray(t.defense) && t.defense.length === 2) t.defense = [t.defense[1], t.defense[1]];\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#97 - the quote never says which item the trader text named",
     "file": "tv/d2jsp_chrome.py",
     "find": "            out[\"resolved\"] = _rn\n",
     "replace": "            pass\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
