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

    def test_the_search_draws_them_for_the_item_the_console_resolved(self):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("+ d2jspTierCardsHtml((j && typeof j.resolved === 'string' && j.resolved) || parsed.item, j && j.db)", src,
                      "the price search never draws the two cards, or not for the item the console resolved")


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
    {"why": "#97 - the price search never draws the NORMAL / PERFECT cards",
     "file": "bible.html",
     "find": "        + d2jspTierCardsHtml((j && typeof j.resolved === 'string' && j.resolved) || parsed.item, j && j.db)   /* #97 */\n",
     "replace": "",
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
