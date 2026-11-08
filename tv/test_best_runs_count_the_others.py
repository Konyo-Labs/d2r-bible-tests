# -*- coding: utf-8 -*-
"""v3887 (#155, REG-3466) - BEST RUNS COUNTS THE OTHERS: A MISSING UNIQUE JOINS THE RUN QUICK WINS RANKS FIRST FOR IT.

His 11-08, with silospen's Monster Type All open at MF 100: Bane Ash's #1 is Coldcrow (Cave Level 1, 1:1455) and Lenymo's
are the Cow King, The Banished and Pitspawn Fouldog - "the best runs should be giving from and out of the OTHERS ... as a best
run it should show for sure as an option for number 1". The F-Uniques Best runs view grouped every missing unique under its
best BOSS (_bestSrc reads the boss drop tables only), so a repeatable super-unique that beats every boss could never be a run
there. The scan now asks _bestRun: the first repeatable place of _qwLists' Combined list (the one ranking Quick wins uses,
bosses and super-uniques together). The Cow King and random packs are never a repeatable run (a Cow King kill bars that
character's cow level); a run card names the better one-kill option beside its drops.

Drives the page's own registry, drop engine and Quick wins ranker in node (the cuts test_the_item_card_ranks_like_quick_wins
uses, plus QW_TARGETS / QW_PLACES / PLACE_PF), and holds the scan's source to asking that ranker. RED_PROOF below.
[[the-unjoined-end]]
"""
import io
import json
import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


def _line(src, start):
    return next(ln for ln in src.split("\n") if ln.startswith(start))


SCENARIO = r"""
var out = {};
mf = 100; players = 1;
["Bane Ash", "Lenymo"].forEach(function(n){
  var x = ITEM_REGISTRY[n];
  var L = _qwLists(_qwPlaces(x), []);
  var top = L.all.filter(function(r){ return r.p; })[0];
  out[n] = { best: top ? top.p.label : null, boss: (L.boss[0] && L.boss[0].p) ? L.boss[0].p.label : null,
             once: (_qwAlso(x, null, 1) || []).map(function(a){ return [a.who, Math.round(a.chance), a.kind]; }) };
});
process.stdout.write(JSON.stringify(out));
"""


def _run(src):
    prelude = ("var window = {}; var document = { getElementById: function(){ return null; } };\n"
               "var ITEMS = []; var mf = 300, players = 1; var _TZ_CHAR_LVL = null;\n")
    # BOSSES sits above the cuts; QW_TARGETS / QW_PLACES / PLACE_PF ride inside the engine cut already
    data = _line(src, "const BOSSES = ").replace("const ", "var ", 1)
    registry = _cut(src, "const ITEM_REGISTRY = {};", "window.ITEM_REGISTRY = ITEM_REGISTRY;")
    engine = _cut(src, "const effMF = (gMF, factor) =>", "// GRAIL-FARM BRIDGE")
    seam = _cut(src, "  var _MFB_BASE = {", "  window._fAdjC = _adjC;")
    ranker = _cut(src, "  var _QW_DIFF = ", "  function _qwRunsTxt(n){")
    prog = prelude + data + "\n" + registry + "\n" + engine + "\n" + seam + "\n" + ranker + "\n" + SCENARIO
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise AssertionError("node could not run the page's ranker - UNKNOWN, not passing: " + (r.stderr or r.stdout)[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])


@unittest.skipUnless(NODE, "node is required to drive the page's own ranker - UNMEASURED without it")
class BestRunsCountTheOthers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        cls.o = _run(cls.src)

    def test_bane_ashs_best_run_is_coldcrow_not_a_boss(self):
        """* THE POINT - silospen's All #1 at MF 100 is Coldcrow (1:1455); the best BOSS is another run"""
        o = self.o["Bane Ash"]
        self.assertEqual(o["best"], "Normal Coldcrow", "Bane Ash's best repeatable run is not Coldcrow: %r" % o)
        self.assertNotEqual(o["boss"], o["best"], "PREMISE: the best boss and the best run are the same - the law cannot see the change")

    def test_lenymos_best_run_is_a_repeatable_one_and_the_cow_king_is_named(self):
        o = self.o["Lenymo"]
        self.assertEqual(o["best"], "Normal Pitspawn Fouldog", "Lenymo's best repeatable run is not Fouldog: %r" % o)
        self.assertTrue(o["once"] and "Cow King" in o["once"][0][0] and o["once"][0][2] == "once",
                        "the Cow King is not Lenymo's named one-kill option: %r" % o)

    def test_the_scan_groups_by_that_ranking(self):
        scan = _cut(self.src, "    var _bestRun=function(x){", "    var runs=Object.keys(bySrc)")   # the Uniques scan (Sets has its own bySrc)
        self.assertEqual(scan.count("var L=_qwLists(_qwPlaces(x), []), top=L.all.filter(function(r){ return r.p; })[0];"), 1,
                         "the Best runs scan no longer asks the one ranking")
        self.assertEqual(scan.count("var b=_bestRun(x); var key=b?b.s.boss:"), 1, "missing uniques are not grouped by _bestRun")
        card = _cut(self.src, "  function _runCard(r,i){", "\n  }\n")
        self.assertIn("better odds in one kill", card, "PREMISE: the one-kill option line is gone from the run card")
        # the line must reach the card's markup, not only be built: the return joins it between the chips and the drawer
        self.assertIn("+chips+'</div>'+optLine+more+", card, "a run card builds the one-kill option and never draws it")


RED_PROOF = [
    {"why": "v3887 (#155) - Best runs groups by the best BOSS again (Bane Ash's Coldcrow is never a run)",
     "file": "bible.html",
     "find": "      var b=_bestRun(x); var key=b?b.s.boss:'Anywhere — no verified source yet';\n",
     "replace": "      var b=_bestSrc(x); var key=b?b.s.boss:'Anywhere — no verified source yet';\n",
     "matches": 1},
    {"why": "v3887 (#155) - the run card stops naming the one-kill option (the Cow King for Lenymo)",
     "file": "bible.html",
     "find": "      +'<div class=\"gf-chips\">'+chips+'</div>'+optLine+more+'</div>'+bossBtn+'</div></div>';\n",
     "replace": "      +'<div class=\"gf-chips\">'+chips+'</div>'+more+'</div>'+bossBtn+'</div></div>';\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
