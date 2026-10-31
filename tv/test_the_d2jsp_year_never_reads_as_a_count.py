# -*- coding: utf-8 -*-
"""v3848 (Elad 03:20, live v3846) - THE YEAR NEVER READS AS A COUNT.

PRICE SEARCH 'shako' said "Reading 2026 posts for shako." - he read 2026 as the number of posts. Every d2jsp
search line that names the price window's year says it is a DATE ("dated 2026 or later"), never "<year> posts".
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")


class TheD2jspYearNeverReadsAsACount(unittest.TestCase):
    def test_no_line_puts_a_year_before_posts(self):
        src = open(BIBLE, encoding="utf-8").read()
        bad = re.findall(r"'[^'\n]*\b20\d\d (?:posts?|post on)\b[^'\n]*'", src)
        self.assertEqual(bad, [], "a d2jsp line reads the year as a count: %r" % bad[:3])

    def test_no_default_or_placeholder_text_puts_a_year_before_posts(self):
        """v3849 - the price box's DEFAULT text said '2026 posts on board 268 only' on every open: an HTML text node,
        which the quoted-string scan above never read. Comments stripped, every text node, quoted string and
        placeholder/title/aria-label value is read."""
        src = open(BIBLE, encoding="utf-8").read()
        src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
        src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
        year = r"\b20\d\d (?:posts?|post on)\b"
        bad = re.findall(r">[^<>]*" + year + r"[^<>]*<", src)
        bad += re.findall(r'"[^"\n]*' + year + r'[^"\n]*"', src)
        bad += re.findall(r"`[^`]*" + year + r"[^`]*`", src)
        self.assertEqual(bad, [], "default or placeholder text reads the year as a count: %r" % bad[:3])

    def test_the_price_box_opens_saying_a_date(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertIn('aria-live="polite">Reads d2jsp posts dated 2026 or later, board 268 only.', src)

    def test_the_search_says_what_it_reads(self):
        src = open(BIBLE, encoding="utf-8").read()
        self.assertIn("'Reading d2jsp posts dated 2026 or later for '", src)


RED_PROOF = [
    {"why": "v3849 - the price box opens reading the year as a post count again",
     "file": "../bible.html",
     "find": 'aria-live="polite">Reads d2jsp posts dated 2026 or later, board 268 only.',
     "replace": 'aria-live="polite">2026 posts on board 268 only.',
     "matches": 1},
    {"why": "v3848 - the search line reads the year as a count again",
     "file": "../bible.html",
     "find": "'Reading d2jsp posts dated 2026 or later for '",
     "replace": "'Reading 2026 posts for '",
     "matches": 1},
    {"why": "v3848 - the no-roll line reads the year as a count again",
     "file": "../bible.html",
     "find": "' No post dated 2026 or later wrote a roll like '",
     "replace": "' No 2026 post wrote a roll like '",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
