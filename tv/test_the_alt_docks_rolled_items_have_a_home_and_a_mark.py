# -*- coding: utf-8 -*-
"""v3850 SB-2/SB-3 (GB-L standing-bugs scan, pass-1204 and pass-1709, 2026-10-31) - THE ALT DOCK'S ROLLED ITEMS.

Seen in the ALT shadow's Unsorted dock: Artisan's Spired Helm of the Mammoth, Viper Eye Jewel, Grim Harness and Bramble
Song with "nothing on the board recognises this name" (SB-2), and Bramble Song drawn as the bare missing-art mark (SB-3).
Measured on this tree (the whole page in node): v3849's rolled-name intake routes all four to MAGIC & RARE; this pins it.
Bramble Song's suffix names only a class (itype weap), so no base can be drawn: _artRolledBase now gives its mark the
class glyph and the question ("a rare weapon - which one?") instead of the bare '?', never a guessed base picture.

RED_PROOF below.
"""
import json, os, sys, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from console_safe import enable; enable()
import vault_page_node as VPN  # noqa: E402

NAMES = ["Artisan's Spired Helm of the Mammoth", "Viper Eye Jewel", "Grim Harness", "Bramble Song"]
BODY = r"""
var r = {};
%s.forEach(function(n){ var s = suggestMule(n); r[n] = {id: s && s.id, art: artOr(n, '\u25c6', 'sm')}; });
OUT.r = r;
""" % json.dumps(NAMES)

RED_PROOF = [
    {"why": "a class-only rare draws the bare mark again",
     "file": "bible.html",
     "find": "    if (_rb.glyph) fallbackHtml = _rb.glyph;   /* v3850 SB-3 the class glyph, with the question as its title */\n",
     "replace": "",
     "matches": 1},
    {"why": "a class-only rare carries no question",
     "file": "bible.html",
     "find": "      out.ask = 'a rare ' + _ART_CLASS_GLYPH[_irB.itypes[0]][1] + ' - which one? the name does not say; a tooltip look settles it';\n",
     "replace": "",
     "matches": 1},
]


class TheDocksRolledItems(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = VPN.run(BODY, timeout=300)["r"]

    def test_each_has_a_mule(self):
        for n in NAMES:
            self.assertEqual(self.r[n]["id"], "magic-rare", n)

    def test_each_has_a_picture_or_a_class_mark_with_its_question(self):
        for n in NAMES[:3]:
            self.assertIn("<img", self.r[n]["art"], n)
        b = self.r["Bramble Song"]["art"]
        self.assertIn("a rare weapon - which one?", b)
        self.assertIn("\u2694", b)
        self.assertNotIn("\u25c6", b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
