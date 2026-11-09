# -*- coding: utf-8 -*-
"""v3892 (#135, REG-3547) - SOCKET FILLERS ARE THE PAGE'S OWN RUNE, GEM AND JEWEL TABLES.

His ask: one shared socket-filler vocabulary (every rune, every gem x grade, every jewel by
name — from the page's own tables, never typed) and one reader. `socketFillerVocab` walks
RUNES, GEM_TYPES, COLOSSAL_JEWELS and ITEMS whose base is a Jewel; it also keeps the
trader spelling "Ber Rune" next to "Ber". `readSocketFillers` picks those names out of a
line, longest first, so "Perfect Ruby" is not also read as "Ruby".
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


def _fn(src, sig, end_sig):
    if src.count(sig) != 1:
        raise AssertionError("%r occurs %d times" % (sig, src.count(sig)))
    i = src.index(sig)
    j = src.index(end_sig, i)
    return src[i:j]


class SocketFillersComeFromThePageTables(unittest.TestCase):

    def test_the_vocab_walks_the_page_tables_and_does_not_type_names(self):
        body = _fn(_src(), "function socketFillerVocab(){", "function readSocketFillers(text){")
        self.assertIn("RUNES", body)
        self.assertIn("GEM_TYPES", body)
        self.assertIn("COLOSSAL_JEWELS", body)
        self.assertIn("ITEMS", body)
        self.assertIn("nm + ' Rune'", body)
        self.assertNotIn('"Ber"', body)
        self.assertNotIn("'Rainbow Facet'", body)

    def test_the_reader_picks_the_longest_filler_names(self):
        if NODE is None:
            self.fail("node is not on this machine - this law does not skip")
        src = _src()
        code = _fn(src, "function socketFillerVocab(){", "const GEM_CRAFT_ROLE")
        harness = r"""
var window = {};
const RUNES = [{n:'Ber'}, {n:'Cham'}];
const GEM_TYPES = [{q:[{name:'Ruby'}, {name:'Perfect Ruby'}]}];
const COLOSSAL_JEWELS = [{n:"Defender's Bile"}];
const ITEMS = [{n:'Rainbow Facet', base:'Jewel'}, {n:'Harlequin Crest', base:'Shako'}];
""" + code + r"""
const line = "Shako socketed with Cham, a Perfect Ruby and Rainbow Facet";
const names = socketFillerVocab();
const read = readSocketFillers(line);
process.stdout.write(JSON.stringify({ names: names, read: read }));
"""
        r = subprocess.run([NODE, "-"], input=harness, capture_output=True, text=True,
                           encoding="utf-8", timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[-400:] if r.stderr else r.stdout[-400:])
        out = json.loads(r.stdout)
        for need in ("Ber", "Ber Rune", "Cham", "Perfect Ruby", "Ruby", "Defender's Bile", "Rainbow Facet"):
            self.assertIn(need, out["names"], "vocab missed %s: %s" % (need, out["names"]))
        self.assertNotIn("Harlequin Crest", out["names"], "a helm was listed as a socket filler")
        self.assertIn("Cham", out["read"])
        self.assertIn("Perfect Ruby", out["read"])
        self.assertIn("Rainbow Facet", out["read"])
        self.assertNotIn("Ruby", out["read"], "Perfect Ruby was also counted as Ruby: %s" % out["read"])


RED_PROOF = [
    {"why": "v3892 (#135, REG-3547) - the vocab no longer walks the page's rune table",
     "file": "bible.html",
     "find": "  (typeof RUNES !== 'undefined' && RUNES ? RUNES : []).forEach(function(r){\n",
     "replace": "  [].forEach(function(r){\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
