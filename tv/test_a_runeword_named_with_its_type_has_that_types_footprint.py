# -*- coding: utf-8 -*-
"""v3895 (#38, REG-3593) - A RUNEWORD NAMED WITH ITS TYPE HAS THAT TYPE'S FOOTPRINT.

Spirit's preferred bases are a sword and a shield, so a bare "Spirit" stays the
1x2 guess (by design: one name, two item types). "Spirit (sword)" and
"Spirit (shield)" name one type; they now take that type's preferred size
(Crystal Sword 2x3, Monarch 2x3) instead of the guess. Paladin-shield (2x2)
Spirit still needs its own qualifier later.
RED_PROOF below.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _enable  # noqa: E402
_enable()

BIBLE = os.path.join(HERE, "..", "bible.html")
NODE = os.environ.get("NODE") or shutil.which("node")


def _fn(src, name):
    m = re.search(r"\bfunction %s\s*\(" % re.escape(name), src)
    if not m:
        raise AssertionError("could not find function %s in bible.html" % name)
    i = src.index("{", m.start())
    depth, j = 0, i
    while j < len(src):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError("unbalanced braces extracting %s" % name)


def _object_from(src, token):
    i = src.find(token)
    if i < 0:
        raise AssertionError("missing %s" % token)
    b = src.index("{", i)
    depth, j, q = 0, b, None
    while j < len(src):
        c = src[j]
        if q:
            if c == "\\":
                j += 2
                continue
            if c == q:
                q = None
        elif c in ("'", '"'):
            q = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[i:j + 1]
        j += 1
    raise AssertionError("unbalanced %s" % token)


def _cb_text(src):
    a = src.find('<script type="application/json" id="cb-db">')
    if a < 0:
        raise AssertionError("the builder database block is not on the page")
    b = src.find("</script>", a)
    return src[src.find(">", a) + 1:b]


class ARunewordNamedWithItsTypeHasThatTypesFootprint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not NODE:
            raise AssertionError("node is not on this machine — this law does not skip")
        with open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        cb_fns = "\n".join(_fn(cls.src, n) for n in (
            "_cbDb", "_cbBase", "_cbFoot", "_cbMaxSock", "_cbBasesOf"))
        rw_bis = _object_from(cls.src, "var RW_BIS = {")
        body = _fn(cls.src, "_runewordCells")
        prog = r"""
var window = globalThis;
var DB = null, DB_ERR = '';
var document = { getElementById: function(id){
  return id === 'cb-db' ? { textContent: %s } : null;
} };
%s
window._cbDb = _cbDb;
window._cbFoot = _cbFoot;
window._cbBasesOf = _cbBasesOf;
%s
var RUNEWORD_TIP = {"Spirit": {b: "4 socket Swords or Shields"}, "Exile": {b: "4 socket Paladin Shields"}};
function findRuneword(name){
  if (RUNEWORD_TIP[name]) return name;
  var k = String(name || '').replace(/\([^)]*\)/g, '').trim();
  return RUNEWORD_TIP[k] ? k : null;
}
%s
_cbDb();
var out = {
  bare: _runewordCells('Spirit'),
  sword: _runewordCells('Spirit (sword)'),
  shield: _runewordCells('Spirit (shield)'),
  swords: _runewordCells('Spirit (swords)')
};
process.stdout.write(JSON.stringify(out));
""" % (json.dumps(_cb_text(cls.src)), cb_fns, rw_bis, body)
        p = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            raise AssertionError((p.stderr or p.stdout)[-2000:])
        cls.f = json.loads(p.stdout)

    def test_a_bare_spirit_stays_the_guess_and_a_typed_one_is_sized(self):
        bare, sword, shield = self.f["bare"], self.f["sword"], self.f["shield"]
        self.assertTrue(bare.get("approx"), bare)
        self.assertEqual([bare["w"], bare["h"]], [1, 2], bare)
        self.assertNotIn("approx", sword, sword)
        self.assertEqual([sword["w"], sword["h"]], [2, 3], sword)
        self.assertNotIn("approx", shield, shield)
        self.assertEqual([shield["w"], shield["h"]], [2, 3], shield)
        self.assertEqual(self.f["swords"], sword)

    def test_the_sizer_asks_the_qualifier(self):
        self.assertIn("  if (_want) {\n    var _pf = [];\n", self.src)


RED_PROOF = [
    {"why": "v3895 (#38, REG-3593) - a typed Spirit falls back to the two-type guess again",
     "file": "bible.html",
     "find": "  if (_want) {\n    var _pf = [];\n",
     "replace": "  if (false) {\n    var _pf = [];\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
