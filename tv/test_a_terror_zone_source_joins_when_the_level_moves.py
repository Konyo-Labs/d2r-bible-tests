# -*- coding: utf-8 -*-
"""v3887 (#156, REG-3465) - A TERROR-ZONE CELL WITH A LEVEL TABLE IS A SOURCE AT EVERY LEVEL, SO MOVING THE LEVEL ADDS IT.

The Grok second eye on v3885 (#231, REG-3437 "findings"): "a registry source row is created only when the terror-zone cell
has a number at page load. Tyrael's Might from Hell TZ Mephisto is 0 in the level table from 68 through 87, so a page loaded
at 68 creates no source row for it. After the slider moves to 94 on that same page, the cell reads 1:20975 and the source
list stays empty. Quick wins, Best runs, and the item card read that list". The registry now makes the source for every cell
that carries a level getter: its odds follow the level, and while the level gives none it says why (a `blocked` reason, the
contract every null-odds source here keeps), so a reader skips it exactly as before.

Drives the page's own level block and registry build (cut from bible.html) in node, the page "loaded" at level 68 through
the same LSR read it uses, then the level moved to 94. RED_PROOF below. [[the-unjoined-end]] [[stale-reading]]
"""
import io
import json
import os
import sys
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _console_safe_enable   # it prints non-ASCII: never crash while REPORTING
    _console_safe_enable()
except Exception:
    pass
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


@unittest.skipUnless(NODE, "node is required to drive the page's own registry build - UNMEASURED without it")
class ATerrorZoneSourceJoinsWhenTheLevelMoves(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            src = fh.read()
        tab = __import__("re").search(r'<script type="application/json" id="tz-level-odds">(.*?)</script>', src, 16).group(1)
        i = src.index("const BOSSES = [") + len("const BOSSES = ")
        bosses, _ = json.JSONDecoder().raw_decode(src[i:])
        block = _cut(src, "const TZ_LEVEL_ODDS = ", "/* v1717 — published so the routing helpers")
        prog = ("var TABLE = %s;\n"
                "var window = { LSR: { getItem: function(k){ return k === 'd2r_charLevel' ? '68' : null; } } };\n"
                "var document = { getElementById: function(id){ return id === 'tz-level-odds' ? { textContent: TABLE } : null; } };\n"
                "var BOSSES = %s;\nvar ITEMS = [];\n" % (json.dumps(tab), json.dumps(bosses))
                + block + "\n" + r"""
function src(item, boss, dk){ return ((ITEM_REGISTRY[item] || {}).sources || []).filter(function(s){ return s.bossId === boss && s.diffKey === dk; })[0] || null; }
var out = { loadLvl: _TZ_CHAR_LVL };
var s = src("Tyrael's Might", 'mephisto', 'hellTz');
out.present = !!s;
out.at68 = s ? [s.chance, s.blocked || null] : null;
_TZ_CHAR_LVL = 94;
out.at94 = s ? [s.chance, s.blocked || null] : null;
var plain = src("Tyrael's Might", 'diablo', 'hellTz');
out.diablo94 = plain ? [plain.chance, plain.blocked || null] : null;
process.stdout.write(JSON.stringify(out));
""")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError("node could not run the page's registry build - UNKNOWN, not passing: %s" % r.stderr[-1500:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])

    def test_premise_the_page_loaded_at_68(self):
        self.assertEqual(self.o["loadLvl"], 68, "PREMISE: the page did not read level 68 at load: %r" % self.o)

    def test_the_source_exists_though_the_load_level_gives_none(self):
        """* THE POINT - loaded at 68 (Hell TZ Mephisto gives Tyrael's Might nothing there), the source is still made"""
        self.assertTrue(self.o["present"], "no Hell TZ Mephisto source for Tyrael's Might when loaded at 68 (REG-3437's finding)")
        chance, why = self.o["at68"]
        self.assertFalse(chance and chance > 0, "at 68 the source claims odds the table does not give: %r" % (self.o["at68"],))
        self.assertIn("not at character level 68", why or "", "a null-odds source says no why: %r" % (self.o["at68"],))

    def test_moving_the_level_to_94_gives_it_its_odds(self):
        chance, why = self.o["at94"]
        self.assertTrue(chance and 19000 < chance < 23000, "at 94 the source does not read its table's 1:~20,975: %r" % (self.o["at94"],))
        self.assertIsNone(why, "a source with odds still says it is blocked: %r" % (self.o["at94"],))

    def test_a_source_with_odds_at_load_is_unchanged(self):
        """baseline: Hell TZ Diablo had odds at load and keeps the live getter it always had"""
        chance, why = self.o["diablo94"]
        self.assertTrue(chance and chance > 0, "Hell TZ Diablo lost its odds: %r" % (self.o["diablo94"],))
        self.assertIsNone(why)


RED_PROOF = [
    {"why": "v3887 (#156) - a level-table cell empty at load makes no source again (REG-3437's second-eye finding)",
     "file": "bible.html",
     "find": "      if ((chance !== null && chance !== undefined) || _live) {\n",
     "replace": "      if (chance !== null && chance !== undefined) {\n",
     "matches": 1, "needs": "node"},
    {"why": "v3887 (#156) - a null-odds level source says no why (readers that print a reason print nothing)",
     "file": "bible.html",
     "find": "            ? `not at character level ${_TZ_CHAR_LVL || 99} - its terror-zone level table` : undefined; }, enumerable: true, configurable: true });\n",
     "replace": "            ? undefined : undefined; }, enumerable: true, configurable: true });\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
