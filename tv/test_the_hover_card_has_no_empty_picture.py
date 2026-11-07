# -*- coding: utf-8 -*-
"""REG-3334 (#73 - GrokBot 6689949990, his Mac and the ALT, v3872: "ONE OPEN: an anonymous <img> with empty src that IS
visible on the board (no id/class/alt)") - THE FLOATING HOVER CARD'S PICTURE IS BORN HIDDEN AND NAMED.

MEASURED on a sandbox render of /board?app=1 at 1440: the one visible empty-src image is `#arttip > img`, the floating hover
card's picture before the first hover. The card sits at opacity 0, so no pixel showed, but the image was born with no src
and no hidden state - and every census of broken pictures (offsetParent + empty src) counted it. Held on the source: the
card's birth markup gives its picture a class and display:none, and every statement in the card's builder that sets the
picture's src also sets its display, so it can never show as an empty frame. RED_PROOF below.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIRTH = "tip.innerHTML='<img class=\"att-img\" alt=\"\" style=\"display:none\"><div class=\"att-name\"></div>"


class TheHoverCardHasNoEmptyPicture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            cls.src = fh.read()
        a = cls.src.index("tip.id='arttip'")
        cls.block = cls.src[a:a + 40000]

    def test_the_picture_is_born_hidden_and_named(self):
        self.assertEqual(self.src.count("tip.id='arttip'"), 1, "PREMISE: the hover card is built in one place")
        self.assertIn(BIRTH, self.block, "the hover card's picture is born with no class and no hidden state - an empty "
                                         "frame every census counts as a broken picture")

    def test_every_picture_write_also_sets_its_display(self):
        writes = re.findall(r"img\.src = [^;]+;[^\n]*", self.block)
        self.assertGreaterEqual(len(writes), 6, "PREMISE: fewer than 6 picture writes found - the block was not read")
        bare = [w[:80] for w in writes if "img.style.display = " not in w]
        self.assertEqual(bare, [], "a path gives the card a picture and leaves its display as it was: %r" % bare)


RED_PROOF = [
    {"why": "REG-3334 - the hover card's picture is born an anonymous empty <img> again (GrokBot's one visible empty image)",
     "file": "bible.html",
     "find": "tip.innerHTML='<img class=\"att-img\" alt=\"\" style=\"display:none\"><div class=\"att-name\"></div>",
     "replace": "tip.innerHTML='<img alt=\"\"><div class=\"att-name\"></div>",
     "matches": 1},
    {"why": "REG-3334 - a path sets the card's picture without its display",
     "file": "bible.html",
     "find": "        img.src = wurl; img.style.display = '';\n",
     "replace": "        img.src = wurl;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
