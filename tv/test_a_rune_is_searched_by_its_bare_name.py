# -*- coding: utf-8 -*-
"""#30 (REG-3628) - A RUNE IS SEARCHED ON d2jsp BY ITS BARE NAME, AND 'ber' IS A WHOLE WORD.

Rune searches went out as the phrase "ber rune", so a listing written "x50 Ber 195fg ea" was missed
both at the search box and when the line was read (the forms required the word "rune"). The query is
now the bare rune name (Ber, Jah, Shael, ...). Matching stays a whole word, so "ber" does not hit
"berry" or "number", and bare "eth" is not the ethereal flag on another item ("eth 4os shako").
Measured on the shipped worker in node; no live d2jsp call. RED_PROOF below.
"""
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
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

WORKER = os.path.join(ROOT, "functions", "api", "d2jsp_quote.js")
NODE = shutil.which("node")
DAY = "Nov 7, 2026"

DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const ctx = { console, Date, Math, JSON, String, Number, Object, Array, RegExp, parseInt, isFinite };
vm.createContext(ctx);
vm.runInContext(src.replace(/^export\s+/mg, ''), ctx);
const out = {};
out.ber = ctx.d2jspSearchWords('Ber Rune');
out.jah = ctx.d2jspSearchWords('Jah Rune');
out.shael = ctx.d2jspSearchWords('Shael Rune');
out.shako = ctx.d2jspSearchWords('Harlequin Crest').query;
const ber = out.ber.forms, eth = ctx.d2jspSearchWords('Eth Rune').forms;
out.listing = ctx.d2jspNamed('x50 Ber 195fg ea', ber);
out.berry = ctx.d2jspNamed('the berry stand 10fg', ber);
out.number = ctx.d2jspNamed('number of items 10fg', ber);
out.ethFlag = ctx.d2jspNamed('eth 4os shako 200fg', eth);
out.ethRune = ctx.d2jspNamed('10 Eth Rune 20fg', eth);
out.ethBare = ctx.d2jspNamed('x10 Eth 20fg ea', eth);
const posts = ctx.d2jspPosts(process.argv[3] + '\nx50 Ber 195fg ea', 'Ber Rune', Date.UTC(2026, 10, 8));
out.posts = posts.map(r => ({ fg: r.fg, perfect: !!r.perfect }));
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to run the shipped d2jsp parser")
class ARuneIsSearchedByItsBareName(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        r = subprocess.run([NODE, "-", WORKER, DAY], input=DRIVER, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node failed: %s" % (r.stderr or r.stdout)[-400:])
        cls.o = json.loads(r.stdout)

    def test_the_query_is_the_bare_rune_name(self):
        """* THE POINT: Ber, Jah, Shael search as themselves, never as 'ber rune'"""
        self.assertEqual(self.o["ber"]["query"], "Ber")
        self.assertEqual(self.o["jah"]["query"], "Jah")
        self.assertEqual(self.o["shael"]["query"], "Shael")
        self.assertIn("ber", self.o["ber"]["forms"])
        self.assertEqual(self.o["shako"], "shako", "a slang item's query drifted")

    def test_a_listing_that_writes_the_bare_name_is_read(self):
        """* THE POINT: 'x50 Ber 195fg ea' is a Ber Rune listing at 195 fg"""
        self.assertTrue(self.o["listing"], "x50 Ber 195fg ea was not named as Ber")
        self.assertEqual(self.o["posts"], [{"fg": 195, "perfect": False}],
                         "the bare-name listing was not priced: %r" % self.o["posts"])

    def test_a_bare_rune_name_is_a_whole_word(self):
        """* THE POINT: 'ber' does not match berry/number, and bare 'eth' is not ethereal"""
        self.assertFalse(self.o["berry"], "berry matched Ber")
        self.assertFalse(self.o["number"], "number matched Ber")
        self.assertFalse(self.o["ethFlag"], "eth 4os shako was read as Eth Rune")
        self.assertTrue(self.o["ethRune"], "10 Eth Rune was not named as Eth")
        self.assertTrue(self.o["ethBare"], "x10 Eth 20fg ea was not named as Eth")


RED_PROOF = [
    {"why": "#30 - a rune is searched as 'ber rune' again, so 'x50 Ber' is missed",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    /* REG-3628 query: the bare rune name (Ber, Jah, ...), never the phrase \"ber rune\" */\n"
             "    return { query: rune.charAt(0).toUpperCase() + rune.slice(1), slang: slang, simple: simple, forms: forms };\n",
     "replace": "    return { query: simple, slang: slang, simple: simple, forms: forms.filter(function (w) { return w !== rune; }) };\n",
     "matches": 1, "needs": "node"},
    {"why": "#30 - a rune name is a substring again, so 'ber' matches berry",
     "file": "functions/api/d2jsp_quote.js",
     "find": "    if (key === '  ' || folded.indexOf(key) < 0) return false;\n",
     "replace": "    if (key === '  ' || folded.indexOf(key.trim()) < 0) return false;\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
