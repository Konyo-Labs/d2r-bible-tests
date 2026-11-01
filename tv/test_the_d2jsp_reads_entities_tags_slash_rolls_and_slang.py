"""v3847 - THE D2JSP PAGE TEXT IS READ AS A TRADER WROTE IT (Elad, 2026-10-30 15:27, 15:41, 15:42; #230 6524232951).
Simsalara's board-268 post read 'no prices' when the page wrote the apostrophe as &#39; or &rsquo; or wrapped the
name in <b>/<span>: the parser matched the raw markup, not the words. Now entities are decoded after tags go and
inline tags unwrap with no space, so each variant reads the same 35 fg from 11 posts. A 'no prices' reading lists the
posts it read and why each was set aside (no date, older than the window, no fg price) - their why, day and d2jsp
link only, never the line's own words. Slash rolls ('anni 20/20/10 1200fg') are fit like roll columns: a post is set
aside only when its roll does not explain its price. The forum's names (anni, torch, gt, jmod, ww...) resolve to their
item for both the search and the line match, and an ambiguous word (doom, gt, gf, storm) is read by its context.
Node only, no Chrome. NO NODE = a declared skip, never a pass. RED_PROOF below. [[regression-guard]]"""
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d2jsp_chrome as D  # noqa: E402

ITEM = "Guardian's Thunder"
LINES = ["+7 -5 4 41 27 15fg", "+7 -6 4 34 30 20fg", "+5 -8 3 37 29 20fg", "+6 -8 3 36 26 25fg", "+7 -7 4 42 23 25fg",
         "+8 -7 4 49 17 35fg", "+10 -6 3 30 30 100fg", "+8 -9 3 47 33 130fg", "+8 -9 4 40 28 140fg",
         "+8 -9 4 46 27 140fg", "+7 -10 4 33 29 390fg"]
NOW = "2026-10-30T07:00:00Z"


def post(name, date="Oct 7 2026 11:04pm"):
    return ('<div>%s <a href="topic.php?t=110445948&amp;f=268&amp;p=695336765">#1</a> Last post: Today</div>'
            "rotw softcore nonladder<br>colossal ancient jewels:<br>" % date
            + "".join("%s %s<br>" % (name, l) for l in LINES))


VARIANTS = {"plain": "guardian's thunder", "numeric entity": "guardian&#39;s thunder",
            "named entity": "guardian&rsquo;s thunder", "bold": "<b>guardian's thunder</b>",
            "span": "<span class=\"x\">guardian</span>'s <i>thunder</i>"}

HAS_NODE = bool(shutil.which("node"))


def js(expr):
    prog = D._read_quote_parser() + "\nprocess.stdout.write(JSON.stringify(" + expr + "));\n"
    return json.loads(subprocess.run(["node", "-"], input=prog, capture_output=True, text=True, timeout=60).stdout)


@unittest.skipUnless(HAS_NODE, "no node on this machine (declared skip)")
class PageText(unittest.TestCase):
    def test_every_markup_variant_reads_the_same_price(self):
        for label, name in VARIANTS.items():
            q = D.parse_public_quote(post(name), ITEM, NOW)
            self.assertEqual("read", q.get("reason"), "%s variant: %r" % (label, q.get("reason")))
            self.assertEqual(11, len(q.get("posts") or []), "%s variant did not price all 11 posts" % label)

    def test_no_prices_lists_what_it_read_and_why(self):
        q = D.parse_public_quote(post("guardian's thunder", date="Oct 7 2024 11:04pm"), ITEM, NOW)
        self.assertEqual("no prices", q.get("reason"))
        aside = q.get("aside") or []
        self.assertEqual(11, len(aside), "the posts set aside are not listed: %r" % aside)
        self.assertTrue(all(a.get("why") for a in aside), "a set-aside post has no reason")
        self.assertTrue(all(set(a) <= {"why", "day", "link"} for a in aside), "a set-aside row carries the line's words")
        self.assertTrue(all("d2jsp.org" in (a.get("link") or "d2jsp.org") for a in aside))


# A d2jsp search card puts the topic link, the date and the price on different lines. The drawer was
# keeping the price and the day, and saying "no link" on every row but the one title that carried its own.
SEARCH_CARDS = (
    '<div class="res"><div><a href="topic.php?t=101&amp;f=268">WTS</a></div>'
    '<div>Oct 31, 2026</div><div>shako 10 fg</div></div>'
    '<div class="res"><div><a href="topic.php?t=102&amp;f=268">ISO</a></div>'
    '<div>Nov 1, 2026</div><div>harlequin crest 60 fg</div></div>'
    '<div class="res"><div>Oct 30, 2026</div>'
    '<div><a href="topic.php?t=103&amp;f=268">shako 15 fg</a></div></div>'
    '<div class="res"><div>Oct 13, 2026 <a href="topic.php?t=104&amp;f=268">#1</a></div><div>shako</div></div>'
    '<div class="res"><div><a href="topic.php?t=105&amp;f=268">shako</a></div><div>Oct 22, 2026</div>'
    '<div>shako</div></div>'
    '<div>Oct 12, 2026 <a href="topic.php?t=201&amp;f=268">#1</a></div><div>shako 40 fg</div>'
    '<div>Oct 13, 2026</div><div>shako 80 fg</div>'
)


@unittest.skipUnless(HAS_NODE, "no node on this machine (declared skip)")
class SearchCardsKeepEachPostsLink(unittest.TestCase):
    def test_every_card_keeps_its_own_post_link(self):
        q = D.parse_public_quote(SEARCH_CARDS, "shako", "2026-11-01T18:00:00Z")
        self.assertEqual(q.get("reason"), "read", q)
        got = [(p.get("fg"), p.get("day"), p.get("link")) for p in q.get("posts") or []]
        self.assertEqual(got, [
            (10, "2026-10-31", "https://forums.d2jsp.org/topic.php?t=101&f=268"),
            (60, "2026-11-01", "https://forums.d2jsp.org/topic.php?t=102&f=268"),
            (15, "2026-10-30", "https://forums.d2jsp.org/topic.php?t=103&f=268"),
            (40, "2026-10-12", "https://forums.d2jsp.org/topic.php?t=201&f=268"),
            (80, "2026-10-13", ""),
        ], got)
        aside = [(a.get("day"), a.get("why"), a.get("link")) for a in q.get("aside") or []]
        self.assertIn(("2026-10-13", "no fg price on the line", "https://forums.d2jsp.org/topic.php?t=104&f=268"), aside)
        self.assertIn(("2026-10-22", "no fg price on the line", "https://forums.d2jsp.org/topic.php?t=105&f=268"), aside)
        self.assertFalse(any(a.get("why") == "no post date read" and a.get("link", "").endswith("t=105&f=268") for a in (q.get("aside") or [])),
                         "the title link was shown as its own undated row: %r" % aside)


@unittest.skipUnless(HAS_NODE, "no node on this machine (declared skip)")
class SlashRolls(unittest.TestCase):
    def test_a_slash_roll_price_is_fit_not_trimmed(self):
        rolls = ["20/20/10 1200fg", "19/19/9 900fg", "18/18/8 700fg", "17/17/7 500fg", "16/16/6 400fg",
                 "20/19/10 1100fg", "18/17/9 650fg", "15/15/5 5000fg"]
        html = ('<div>Oct 20 2026 <a href="topic.php?t=1&amp;f=271&amp;p=2">#1</a></div>'
                + "".join("anni %s<br>" % r for r in rolls))
        q = D.parse_public_quote(html, "Annihilus", NOW)
        posts = q.get("posts") or []
        prices = sorted(p["fg"] for p in posts if p.get("w", 1) > 0)
        self.assertIn(1200, prices, "the perfect anni was trimmed as far from the middle: %r" % q)
        self.assertNotIn(5000, prices, "the 15/15/5 at 5000 fg still counts: %r" % q)
        why = " ".join(str(p.get("out")) for p in posts if p.get("fg") == 5000)
        self.assertIn("roll does not explain its price", why, "the 15/15/5 at 5000 fg was not set aside: %r" % q)


@unittest.skipUnless(HAS_NODE, "no node on this machine (declared skip)")
class Slang(unittest.TestCase):
    def test_forum_words_resolve_to_their_item(self):
        want = {"anni": "Annihilus", "torch": "Hellfire Torch", "gt": "Guardian's Thunder", "shako": "Harlequin Crest",
                "jmod": "Jeweler's Monarch of Deflecting", "ww": "Whirlwind"}
        got = js("[%s].map(function(t){return d2jspResolveItem(t).item;})" % ",".join(json.dumps(k) for k in want))
        self.assertEqual(list(want.values()), got)

    def test_an_ambiguous_word_is_read_by_its_context(self):
        cases = [("doom", "Doom"), ("doom cv", "Doom"), ("doom sword", "Doombringer"), ("gt doom base", "Doom"),
                 ("gf sword", "Grandfather"), ("storm monarch", "Stormshield")]
        got = js("[%s].map(function(t){return d2jspResolveItem(t).item;})" % ",".join(json.dumps(c) for c, _ in cases))
        self.assertEqual([w for _, w in cases], got)

    def test_the_search_asks_by_the_item_and_the_line_match_obeys_context(self):
        self.assertEqual("guardians thunder", js('d2jspSearchWords("gt").query'))
        self.assertEqual("anni", js('d2jspSearchWords("Annihilus").query'))
        self.assertTrue(js('d2jspOtherReading("doom cv eth 4os 900fg", "Doombringer")'))
        self.assertFalse(js('d2jspOtherReading("doom 300fg", "Doombringer")'))

    def test_one_edit_of_a_known_name_is_that_item_and_a_tie_stays_typed(self):
        """Elad 2026-11-01 19:35: PRICE SEARCH 'gaurdian's thunder' read 0 posts. The forum was asked
        for the swapped spelling, so Guardian's Thunder was not on the page."""
        near = {
            "gaurdian's thunder": "Guardian's Thunder",
            "gaurdians thunder": "Guardian's Thunder",
            "gaurdian angel": "Guardian Angel",
            "harlequen crest": "Harlequin Crest",
            "shakoo": "Harlequin Crest",
            "jomd": "Jeweler's Monarch of Deflecting",
            "arachind mesh": "Arachnid Mesh",
            "stormsheild": "Stormshield",
            "annihlius": "Annihilus",
            "torchh": "Hellfire Torch",
            "griffons eye": "Griffon's Eye",
            "deaths web": "Death's Web",
            "war traveller": "War Traveler",
            "kiras gaurdian": "Kira's Guardian",
        }
        exact = ["Guardian's Thunder", "Harlequin Crest", "Annihilus", "Stone of Jordan", "War Traveler",
                 "Arachnid Mesh", "Griffon's Eye", "The Oculus", "shako", "anni", "jmod", "gt", "soj"]
        stay = ["anny", "gaurdain's thunder", "guardian", "zzzzqqqq", "not an item"]
        got_near = js("[%s].map(function(t){return d2jspResolveItem(t).item;})" % ",".join(json.dumps(k) for k in near))
        self.assertEqual(list(near.values()), got_near, got_near)
        got_exact = js("[%s].map(function(t){return d2jspResolveItem(t).item;})" % ",".join(json.dumps(k) for k in exact))
        self.assertEqual(["Guardian's Thunder", "Harlequin Crest", "Annihilus", "Stone of Jordan", "War Traveler",
                          "Arachnid Mesh", "Griffon's Eye", "The Oculus", "Harlequin Crest", "Annihilus",
                          "Jeweler's Monarch of Deflecting", "Guardian's Thunder", "Stone of Jordan"], got_exact)
        got_stay = js("[%s].map(function(t){return d2jspResolveItem(t).item;})" % ",".join(json.dumps(k) for k in stay))
        self.assertEqual(stay, got_stay, got_stay)
        self.assertEqual("guardians thunder", js('d2jspSearchWords("gaurdian\'s thunder").query'))

    def test_a_close_name_still_prices_the_post_and_keeps_its_link(self):
        cards = [
            ("gaurdian's thunder", "guardian's thunder 35 fg", 901, 35),
            ("shako", "shako 10 fg", 902, 10),
            ("harlequen crest", "harlequin crest 25 fg", 903, 25),
            ("jomd", "jmod 80 fg", 904, 80),
            ("arachind mesh", "arachnid mesh 40 fg", 905, 40),
            ("stormsheild", "stormshield 15 fg", 906, 15),
            ("annihlius", "anni 100 fg", 907, 100),
            ("torchh", "torch 50 fg", 908, 50),
            ("deaths web", "deaths web 70 fg", 909, 70),
            ("war traveller", "war travs 30 fg", 910, 30),
        ]
        for typed, line, topic, fg in cards:
            html = ('<div><a href="topic.php?t=%d&amp;f=268">WTS</a></div><div>Nov 1, 2026</div><div>%s</div>'
                    % (topic, line))
            q = D.parse_public_quote(html, typed, "2026-11-01T18:00:00Z")
            posts = q.get("posts") or []
            self.assertEqual(q.get("reason"), "read", "%s: %r" % (typed, q))
            self.assertTrue(posts, typed)
            self.assertEqual(posts[0].get("fg"), fg, typed)
            self.assertEqual(posts[0].get("link"), "https://forums.d2jsp.org/topic.php?t=%d&f=268" % topic, typed)
        junk = D.parse_public_quote(
            '<div><a href="topic.php?t=999&amp;f=268">WTS</a></div><div>Nov 1, 2026</div><div>shako 10 fg</div>',
            "zzzzqqqq", "2026-11-01T18:00:00Z")
        self.assertEqual(junk.get("reason"), "no prices", junk)
        self.assertEqual(junk.get("posts") or [], [])


RED_PROOF = [
    {"why": "entities are not decoded, so &#39; hides the name again",
     "file": "functions/api/d2jsp_quote.js", "find": "function d2jspDecodeEntities(t) {",
     "replace": "function d2jspDecodeEntities(t) { return String(t);", "matches": 1},
    {"why": "an alias no longer resolves to its item",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (D2JSP_SLANG[k].some(function (w) { return w === f; })) return",
     "replace": "    if (false) return", "matches": 1},
    {"why": "a one-letter miss is searched as typed again, so gaurdian's thunder reads 0 posts",
     "file": "functions/api/d2jsp_quote.js",
     "find": "  if (near) return { item: near, via: 'near', ambiguous: false };",
     "replace": "  if (false) return { item: near, via: 'near', ambiguous: false };", "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
