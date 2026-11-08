# -*- coding: utf-8 -*-
"""v3886 (#152) - THE LAWS HAVE ONE COMMENT STRIPPER, AND ITS PRIVATE COPIES MAY ONLY GET FEWER.

v3885's first GitHub round went red on two copies of a comment stripper inside test_control: each read `accept="image/*"`
(a MIME wildcard in the photo-upload <input>) as a comment opener, and once the Chronicle buttons left the page the next
"*/" fell inside the cap, so the strip ate live markup - #funi-body, #tab-fsets, #fsets-body and the Characters ids - and
two markup laws reported elements "looked up and never created". The fix was made twice by hand, in two copies. There
were 184 such regex sites in 119 files under tv/ on 11-08: the same routine, drifting, one copy per law.

tv/js_strip.py is the one stripper. This law holds it to its three rules on a live-markup shape and on the page itself,
and holds the private copies to a ceiling that may only fall (REG-057's ratchet): a law that strips comments calls
js_strip; one that keeps its own copy is counted, and a NEW copy turns this red. Lower the ceiling as copies migrate.
RED_PROOF below. [[copy-drift]] [[source-reading-guard]]
"""
import glob
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import js_strip  # noqa: E402

ROOT = os.path.dirname(HERE)
#: the private copies: 184 on 11-08 (v3886), 181 on 11-09 (v3887 - the Fleet-row law moved to js_strip); MAY ONLY FALL - lower it when a law moves to js_strip
CEILING = 181
#: a block-comment regex a law writes for itself: "/\*" then a bounded or lazy body, or a lookahead
COPY = re.compile(r"/\\\*(?:\.\{0,|\.\*\?|\[\\s\\S\]\*\?|\(\?:\.\|\\n\)\*\?|\(\?!)")
ID = r"\bid\s*=\s*[\\]?['\"]([\w-]+)"


def _copies():
    n, where = 0, {}
    for f in sorted(glob.glob(os.path.join(HERE, "*.py"))):
        if os.path.basename(f) in ("js_strip.py", os.path.basename(__file__)):
            continue
        with io.open(f, encoding="utf-8") as fh:
            k = len(COPY.findall(fh.read()))
        if k:
            n += k
            where[os.path.basename(f)] = k
    return n, where


class OneCommentStripperForTheLaws(unittest.TestCase):

    def test_a_mime_wildcard_is_markup_not_a_comment(self):
        """* THE POINT - v3885 round 1's shape: an <input accept="image/*"> before live ids and a later real comment"""
        src = ('<input type="file" id="shot" accept="image/*" multiple>\n<div id="funi-body"></div>\n'
               '<div id="tab-fsets"><div id="fsets-body"></div></div>\n<style>/* a real comment */ .x{}</style>')
        out = js_strip.strip_js_comments(src)
        self.assertEqual(sorted(re.findall(ID, out)), ["fsets-body", "funi-body", "shot", "tab-fsets"],
                         "the stripper ate live markup after a MIME wildcard")
        self.assertNotIn("a real comment", out, "the stripper kept a real comment")

    def test_it_strips_comments_and_keeps_code(self):
        src = "var a = 1; /* gone */\n// a line comment\nvar u = 'http://x.y/z'; var b = 2;"
        out = js_strip.strip_js_comments(src)
        self.assertNotIn("gone", out)
        self.assertNotIn("a line comment", out)
        self.assertIn("var u = 'http://x.y/z'; var b = 2;", out, "a // inside a string was read as a comment")
        unbounded = "/* " + "x" * (js_strip.CAP + 10) + " */ var keep = 1;"
        self.assertIn("var keep = 1;", js_strip.strip_js_comments(unbounded))

    def test_the_page_keeps_every_id_through_the_stripper(self):
        """the instrument on the real subject: no id= declaration in bible.html is lost to the strip"""
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            raw = fh.read()
        raw_ids = set(re.findall(ID, raw))
        self.assertGreater(len(raw_ids), 400, "PREMISE: the page's ids were not found")
        self.assertEqual(raw_ids - set(re.findall(ID, js_strip.strip_js_comments(raw))), set(),
                         "the shared stripper deleted live markup from bible.html")

    def test_the_private_copies_only_get_fewer(self):
        n, where = _copies()
        self.assertGreater(n, 0, "PREMISE: no private stripper found - the pattern rotted (lower CEILING to 0 if truly gone)")
        self.assertLessEqual(n, CEILING, "a law added its own comment stripper (%d > %d) - call js_strip.strip_js_comments "
                                         "instead: %s" % (n, CEILING, sorted(where.items(), key=lambda x: -x[1])[:8]))


RED_PROOF = [
    {"why": "v3886 (#152) - the shared stripper reads accept=\"image/*\" as a comment again (v3885 round 1's red)",
     "file": "tv/js_strip.py",
     "find": "    src = re.sub(r\"/\\*(?![\\\"']).{0,%d}?\\*/\" % int(cap), \" \", str(src), flags=re.S)\n",
     "replace": "    src = re.sub(r\"/\\*.{0,%d}?\\*/\" % int(cap), \" \", str(src), flags=re.S)\n",
     "matches": 1},
    {"why": "v3886 (#152) - test_control keeps its own stripper copy again (the ceiling must catch a new copy)",
     "file": "tv/test_control.py",
     "find": "        import js_strip   # v3886 (#152) - the laws' ONE stripper (a \"/*\" a quote follows is never a comment: accept=\"image/*\")\n        return js_strip.strip_js_comments(src, cap)\n",
     "replace": "        import re\n        src = re.sub(r\"/\\*.{0,%d}?\\*/\" % int(cap), \" \", src, flags=re.S)\n        return re.sub(r\"(?m)^\\s*//.*$\", \" \", src)\n",
     "matches": 2},
]


if __name__ == "__main__":
    unittest.main()
