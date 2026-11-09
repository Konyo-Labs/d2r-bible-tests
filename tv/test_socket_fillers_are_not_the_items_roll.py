# -*- coding: utf-8 -*-
"""v3893 (#135, REG-3558) - A SOCKET FILLER IS NEVER READ AS THE ITEM'S ROLL.

readSocketFillers already names what is IN the sockets from the page's own tables.
d2jspParseSearch now peels those names (and a slash-roll written next to them) so
"shako 15/15 Rainbow Facet" is a Shako with no held roll, not a 15/15 Shako, and
"shako 141 Ber'd" keeps the 141 as the Shako's defence. A filler-only tooltip line
is skipped by d2jspAffixRead. Vocabulary is never typed a second time.
RED_PROOF below.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


class SocketFillersAreNotTheItemsRoll(unittest.TestCase):

    def test_search_and_affix_call_peelSocketFillers(self):
        src = _src()
        self.assertIn("function peelSocketFillers(text)", src)
        parse = src[src.index("function d2jspParseSearch(text) {"):src.index("function d2jspReadLine")]
        self.assertIn("if (typeof peelSocketFillers === 'function') t = String(peelSocketFillers(t).text", parse)
        affix = src[src.index("function d2jspAffixRead(mods, db, itemName)"):src.index("var D2JSP_FAMILY_MODS")]
        self.assertIn("var _pf = peelSocketFillers(t);", affix)
        self.assertIn("if (_pf.fillers && _pf.fillers.length && !leftover) return;", affix)

    def test_a_filler_is_not_the_held_roll(self):
        if not NODE:
            self.fail("node is not on this machine - this law does not skip")
        src = _src()
        i = src.index("function socketFillerVocab(){")
        code = src[i:src.index("const GEM_CRAFT_ROLE")]
        k = src.index("function d2jspParseSearch(text) {")
        parse = src[k:src.index("\n}", k) + 2]
        js = (
            "var window = {};\n"
            "const RUNES = [{n:'Ber'}, {n:'Cham'}];\n"
            "const GEM_TYPES = [{q:[{name:'Ruby'}, {name:'Perfect Ruby'}]}];\n"
            "const COLOSSAL_JEWELS = [{n:\"Defender's Bile\"}];\n"
            "const ITEMS = [{n:'Rainbow Facet', base:'Jewel'}, {n:'Harlequin Crest', base:'Shako'}];\n"
            + code + parse + "\n"
            "process.stdout.write(JSON.stringify({\n"
            "  slash: d2jspParseSearch('40/15 shako'),\n"
            "  defence: d2jspParseSearch('shako 141'),\n"
            "  ber: d2jspParseSearch(\"shako 141 Ber'd\"),\n"
            "  facet: d2jspParseSearch('shako 15/15 Rainbow Facet'),\n"
            "  cham: d2jspParseSearch('shako Cham')\n"
            "}));\n"
        )
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True,
                           encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-400:] if r.stderr else r.stdout[-400:])
        out = json.loads(r.stdout)
        self.assertEqual((out["slash"]["item"], out["slash"]["roll"]), ("shako", [40, 15]), out)
        self.assertEqual((out["defence"]["item"], out["defence"]["roll"]), ("shako", [141]), out)
        self.assertEqual((out["ber"]["item"], out["ber"]["roll"]), ("shako", [141]), out)
        self.assertEqual(out["facet"]["item"], "shako", out)
        self.assertIsNone(out["facet"]["roll"], "the jewel's 15/15 became the Shako's roll: %s" % out)
        self.assertEqual((out["cham"]["item"], out["cham"]["roll"]), ("shako", None), out)


RED_PROOF = [
    {"why": "v3893 (#135, REG-3558) - a filler's slash-roll is read as the item's roll again",
     "file": "bible.html",
     "find": "  if (typeof peelSocketFillers === 'function') t = String(peelSocketFillers(t).text || '').replace(/\\s+/g, ' ').trim();\n",
     "replace": "  if (false) t = t;\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
