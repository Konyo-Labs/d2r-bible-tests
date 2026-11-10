# -*- coding: utf-8 -*-
"""#30 (REG-3627) - A d2jsp ROLL WRITTEN BEFORE THE ITEM NAME COUNTS, A TOTAL-DEFENSE AFTER IT DOES NOT.

A live board-268 post wrote "1os 141 Shako *5 ea=100fg" and "141 Shako *5 ea=80fg"
(https://forums.d2jsp.org/topic.php?t=110575834&f=268&p=696169600). The parser already read a
perfect 141 off "141Def" / "141def" after the name, but a number standing immediately before
Shako was not a roll, so those listings were not perfect. A number in the item's roll range
adjacent before the name now counts. A total-defense after the name ("eth perf shako 211",
"mage plate 995 def") is not that roll. Measured on the shipped worker in node; no live d2jsp
call. RED_PROOF below.
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
function perf(item, text) {
  return ctx.d2jspRollPerfect(item, ctx.d2jspNotation(text), text);
}
out.before = perf('Harlequin Crest', '141 Shako *5 ea=80fg');
out.sockets = perf('Harlequin Crest', '1os 141 Shako *5 ea=100fg');
out.after = perf('Harlequin Crest', 'Shako 141def 80fg');
out.low = perf('Harlequin Crest', 'Shako 137 def 30fg');
out.ethTotal = perf('Harlequin Crest', 'eth perf shako 211 ea=80fg');
out.baseDef = perf('Enigma', 'mage plate 995 def 500fg');
const posts = ctx.d2jspPosts(
  process.argv[3] + '\n1os 141 Shako *5 ea=100fg\n' + process.argv[3] + '\n141 Shako *5 ea=80fg',
  'Harlequin Crest', Date.UTC(2026, 10, 8));
out.posts = posts.map(r => ({ fg: r.fg, perfect: !!r.perfect }));
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to run the shipped d2jsp parser")
class AD2jspRollBeforeTheNameCounts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        r = subprocess.run([NODE, "-", WORKER, DAY], input=DRIVER, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node failed: %s" % (r.stderr or r.stdout)[-400:])
        cls.o = json.loads(r.stdout)

    def test_a_roll_written_before_the_name_is_perfect(self):
        """* THE POINT: '141 Shako' and '1os 141 Shako' are the perfect 141 def roll"""
        self.assertIs(self.o["before"], True, "141 Shako was not a perfect roll: %r" % self.o)
        self.assertIs(self.o["sockets"], True, "1os 141 Shako was not a perfect roll: %r" % self.o)
        self.assertEqual(self.o["posts"], [{"fg": 100, "perfect": True}, {"fg": 80, "perfect": True}],
                         "the live listing lines were not both perfect 141s: %r" % self.o["posts"])

    def test_a_post_name_roll_and_a_low_roll_are_unchanged(self):
        self.assertIs(self.o["after"], True, "141def after the name stopped counting")
        self.assertIs(self.o["low"], False, "137 def was treated as perfect")

    def test_a_total_defense_after_the_name_is_not_the_roll(self):
        """* THE POINT: 'eth perf shako 211' and 'mage plate 995 def' are not the item's roll"""
        self.assertIsNone(self.o["ethTotal"], "211 after Shako counted as a roll: %r" % self.o)
        self.assertIsNone(self.o["baseDef"], "995 def on a mage plate counted as Enigma's roll: %r" % self.o)


RED_PROOF = [
    {"why": "#30 - a number in the roll range before the name is ignored again, so '141 Shako' is not perfect",
     "file": "functions/api/d2jsp_quote.js",
     "find": "  d2jspNumsBeforeName(line || (note && note.text) || '', itemName, R).forEach(function (v) { nums.push(v); });\n",
     "replace": "  /* REG-3627 disabled */\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
