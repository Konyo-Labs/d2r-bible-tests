# -*- coding: utf-8 -*-
"""v3889 (#178, REG-3500) - EACH TIER CARD LISTS ITS OWN POSTS: NORMAL'S UNDER NORMAL (LEFT), PERFECT'S UNDER PERFECT (RIGHT).

His words 11-09 ~10:05, with an Enigma price check on screen (NORMAL 400 fg, PERFECT 1,850 fg, and under both one drawer
"hide the 4 posts" mixing them): "the posts for the show history under the items after searching should be connecting to
each individually like.. for the one under and related to the normal tier should be on the left side under it and the
right side under the perfect tier should be showing the posts related to it. so they are separated between a perfect and a
regular", then "it should each show like 4-5 posts individually connected. linked to each normal and each perfect".

Now each card carries its tier's posts, open: the latest five (D2JSP_TIER_POSTS), newest first, each with its own "open
post" link and "(of N)" when there are more - from the live search and from the price database's own kept posts (each
already carries its tier), the same link once. A post is PERFECT when its rolls read perfect (REG-3441) - the flag now
survives the roll-likeness step (d2jspSimilarPrice). The roll-like-yours line is said once above the cards; an item the
page cannot draw keeps the one drawer. Run on the whole page in node (tv/vault_page_node.py, empty storage). RED_PROOF below.
"""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

L = "https://forums.d2jsp.org/topic.php?t=%d&f=268"


def E(i):
    """the link as the card writes it (HTML-escaped)"""
    return (L % i).replace("&", "&amp;")
LIVE = [{"fg": 1850, "day": "2026-11-08", "link": L % 1, "perfect": True, "w": 0.5},
        {"fg": 400, "day": "2026-11-09", "link": L % 2, "w": 1.0}]
DB = {"normal": {"fg": 400, "n": 7}, "perfect": {"fg": 1850, "n": 2},
      "proof": {"posts": [{"fg": 1850, "day": "2026-11-08", "link": L % 1, "tier": "perfect", "w": 0.5},   # the same post as LIVE[0]
                          {"fg": 1400, "day": "2026-11-06", "link": L % 3, "tier": "perfect", "w": 1.0}]
                         + [{"fg": 300 + i, "day": "2026-11-0%d" % (i + 1), "link": L % (10 + i), "tier": "normal", "w": 1.0}
                            for i in range(7)]}}

BODY = r"""
var LIVE = %s, DB = %s;
OUT.cards = window._d2jspTierCardsHtml('Harlequin Crest', DB, LIVE);
OUT.bare = window._d2jspTierCardsHtml('Harlequin Crest', { normal: { fg: 400 }, perfect: { fg: 1850 } }, null);
OUT.sim = d2jspSimilarPrice({ posts: [{ fg: 1850, perfect: true, w: 1, link: 'x' }, { fg: 400, w: 1, link: 'y' }] }, null, 'Harlequin Crest');
""" % (json.dumps(LIVE), json.dumps(DB))


def _card(html, kind):
    i = html.index('data-d2jsp-tier-card="%s"' % kind)
    return html[i:html.index("</figure>", i)]


class EachTierCardListsItsOwnPosts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = VPN.run(BODY, prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300) if VPN.NODE else None

    def setUp(self):
        if self.out is None:
            self.skipTest("node is absent on this machine - the cards are UNMEASURED here, never a pass")

    def test_each_card_holds_only_its_tier(self):
        """* THE POINT - normal posts under NORMAL, perfect posts under PERFECT, each with its own link"""
        n, p = _card(self.out["cards"], "normal"), _card(self.out["cards"], "perfect")
        self.assertIn('data-d2jsp-tier-posts="perfect" open', p)
        self.assertIn('data-d2jsp-tier-posts="normal" open', n)
        for i in (1, 3):
            self.assertIn(E(i), p, "a perfect post is not under PERFECT")
            self.assertNotIn(E(i), n, "a perfect post sits under NORMAL")
        self.assertIn(E(2), n)
        self.assertNotIn(E(2), p, "a normal post sits under PERFECT")

    def test_a_card_lists_the_latest_five_newest_first(self):
        n = _card(self.out["cards"], "normal")
        links = re.findall(r'href="([^"]+)"', n)
        self.assertEqual(len(links), 5, links)
        self.assertEqual(links[0], E(2), "the newest normal post (11-09) is not first")
        self.assertIn("(of 8)", n, "a list cut to five does not say how many there are")
        self.assertEqual(n.count("open post"), 5)

    def test_one_post_is_listed_once(self):
        p = _card(self.out["cards"], "perfect")
        self.assertEqual(p.count(E(1)), 1, "the live post and the database's copy of it are both listed")

    def test_no_posts_means_no_lists(self):
        self.assertNotIn("data-d2jsp-tier-posts", self.out["bare"])

    def test_the_tier_survives_the_roll_likeness_step(self):
        rows = self.out["sim"]["posts"]
        self.assertEqual([r["perfect"] for r in rows], [True, False])


RED_PROOF = [
    {"why": "v3889 (REG-3500) - the cards list no posts again (one mixed drawer under both)",
     "file": "bible.html",
     "find": "        + tier + (_byTier ? d2jspEvidenceHtml(null, null, { rows: _byTier[kind], tier: kind }) : '') + '</figure>';\n",
     "replace": "        + tier + '</figure>';\n",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (REG-3500) - a perfect post lands under NORMAL",
     "file": "bible.html",
     "find": "    var _byTier = _all.length ? { normal: _all.filter(function(p){ return !_isP(p); }), perfect: _all.filter(_isP) } : null;\n",
     "replace": "    var _byTier = _all.length ? { normal: _all, perfect: _all.filter(_isP) } : null;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (REG-3500) - the roll-likeness step drops the tier, so every searched post reads normal",
     "file": "bible.html",
     "find": "             perfect: p.perfect === true || p.tier === 'perfect' };   /* v3889 (#178) - which tier card the post sits under */\n",
     "replace": "             };\n",
     "matches": 1, "needs": "node"},
    {"why": "v3889 (REG-3500) - a tier lists every post it has, not the latest five",
     "file": "bible.html",
     "find": "  if (_tier && rows.length > D2JSP_TIER_POSTS) {",
     "replace": "  if (false) {",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
