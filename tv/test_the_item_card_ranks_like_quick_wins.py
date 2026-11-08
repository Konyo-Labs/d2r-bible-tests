# -*- coding: utf-8 -*-
"""v3886 - THE ITEM CARD RANKS ITS PLACES THE WAY QUICK WINS DOES, AND SAYS SO.

His words 2026-11-08, on Tyrael's Might: "it doesnt list diablo anymore but clearly the top 5 should include diablo ...
and for others obviosuly". The item card (renderItemDetailCard) sorted its places by TIME alone and kept six, so a run with
far better odds but a slow clear fell off it. MEASURED at LVL 90 / MF 500 before the change: Hell TZ Diablo (1:169,358 a
kill, ~3,354 h) sat behind six quicker runs and was missing from Tyrael's Might's card, while silospen (Terror Zone on, the
same MF) lists it fifth and Quick wins showed it fifth.

So the card's places come from itemCardSources(item), which hands them to the ONE ranking Quick wins uses (_qwRank):
fewest RUNS for a 50% chance first; runs within 2% are the same run count and the quicker run leads (his 11-08 ruling).
Its words follow the order: the Quick take says "Best run", never "Fastest", and every row prints RUNS (an area run of
350 cows is one run, not 350).

The page's own code runs in node (cut from bible.html), at several MF and /players settings, on every item the registry
carries; every expectation is re-derived here from the rows' own numbers, never typed. RED_PROOF below.
[[the-unjoined-end]] [[copy-drift]]
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
from console_safe import enable  # noqa: E402
enable()

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")
QW_SAME = 0.02          # his "basically the same" - the ranking's 2% (bible.html QW_SAME)

def _read():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


def _card_fn(src):
    """renderItemDetailCard's own text, to its closing line"""
    return _cut(src, "function renderItemDetailCard(itemName) {", "\n}\n")


SCENARIO = r"""
var out = {};
SETTINGS.forEach(function(st){
  mf = st[0]; players = st[1];
  Object.keys(ITEM_REGISTRY).sort().forEach(function(n){
    var rows = itemCardSources(ITEM_REGISTRY[n]);
    if (rows.length > 1) out[st.join('|') + '|' + n] = rows.map(function(r){ return [r.label, r.runs, r.hrs, r.r50, r.boss]; });
  });
});
process.stdout.write(JSON.stringify(out));
"""

SETTINGS = [[300, 1], [500, 1], [500, 3], [1000, 8]]


def _hrs(h):
    return h if isinstance(h, (int, float)) else 9e9


def _one_ranking(rows):
    """the order _qwRank gives, re-derived from the rows' own numbers: fewest runs; a group is cut from its fewest-runs row
    and holds every row within 2% of it; inside a group the fewest hours lead (then runs, then the name)"""
    srt = sorted(rows, key=lambda r: (r[1], _hrs(r[2]), r[0]))
    want, i = [], 0
    while i < len(srt):
        j = i + 1
        while j < len(srt) and srt[j][1] <= srt[i][1] * (1 + QW_SAME):
            j += 1
        want += sorted(srt[i:j], key=lambda r: (_hrs(r[2]), r[1], r[0]))
        i = j
    return [r[0] for r in want]


def _run(src):
    bl = next(ln for ln in src.split("\n") if ln.startswith("const BOSSES = "))
    registry = _cut(src, "const ITEM_REGISTRY = {};", "window.ITEM_REGISTRY = ITEM_REGISTRY;")
    engine = _cut(src, "const effMF = (gMF, factor) =>", "// GRAIL-FARM BRIDGE")
    seam = _cut(src, "  var _MFB_BASE = {", "  window._fAdjC = _adjC;")
    ranker = _cut(src, "  var _QW_DIFF = ", "  function _qwRunsTxt(n){")
    card = _cut(src, "function itemCardSources(item) {", "try { window.itemCardSources = itemCardSources; }")
    prelude = ("var window = {}; var document = { getElementById: function(){ return null; } };\n"
               "var ITEMS = []; var mf = 300, players = 1;\nvar SETTINGS = %s;\n" % json.dumps(SETTINGS))
    prog = (prelude + bl.replace("const BOSSES", "var BOSSES", 1) + "\n" + registry + "\n" + engine + "\n" + seam + "\n"
            + ranker + "\n" + card + "\n" + SCENARIO)
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=240)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


@unittest.skipUnless(NODE, "node is required to drive the page's own drop math")
class TheItemCardRanksLikeQuickWins(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        cls.o = _run(cls.src)

    def test_the_card_takes_its_places_from_the_one_ranking(self):
        fn = _card_fn(self.src)
        self.assertEqual(fn.count("const sources = itemCardSources(item);"), 1,
                         "renderItemDetailCard no longer takes its places from itemCardSources")
        self.assertNotIn("sources.sort(", fn, "renderItemDetailCard sorts its places itself again - a second ranking")
        self.assertEqual(self.src.count("window._qwRank = _qwRank;"), 1, "Quick wins no longer publishes its ranking")

    def test_every_item_card_is_in_quick_wins_order(self):
        self.assertGreater(len(self.o), 1500, "premise: the registry's items, at four settings, reach the card")
        bad = []
        for k, rows in sorted(self.o.items()):
            got = [r[0] for r in rows]
            want = _one_ranking(rows)
            if got != want:
                bad.append("%s\n      card  %s\n      want  %s" % (k, got[:6], want[:6]))
        self.assertEqual(bad, [], "%d card(s) are not in the one ranking's order:\n  %s" % (len(bad), "\n  ".join(bad[:6])))

    def test_the_cases_can_tell_the_one_ranking_from_time_alone(self):
        """baseline: on these very rows a time-only sort gives a different top six for many items - so the order law above
        measures the ranking, not a coincidence of the data"""
        differ = 0
        for k, rows in self.o.items():
            by_time = [r[0] for r in sorted(rows, key=lambda r: (_hrs(r[2]), r[0]))][:6]
            if by_time != _one_ranking(rows)[:6]:
                differ += 1
        self.assertGreater(differ, 200, "only %d cards differ between the two orders - the law could not see a regression" % differ)

    def test_tyraels_might_keeps_diablo_on_its_card(self):
        """his case, on the page's own stored Terror Zone figures (level 99 - the LVL setting moves them, the rule does not)"""
        rows = self.o.get("500|1|Tyrael's Might")
        self.assertTrue(rows, "Tyrael's Might reached no card")
        top6 = [r[4] for r in rows[:6]]
        self.assertTrue(any("Diablo" in b for b in top6), "Tyrael's Might's card lost Diablo: %s" % top6)

    def test_the_words_follow_the_order(self):
        fn = _card_fn(self.src)
        self.assertNotIn("Fastest = <span", fn, "the Quick take calls the fewest-runs place the fastest")
        self.assertEqual(fn.count("Best run = <span class=\"gic-item-link\">${best.boss}</span>"), 1,
                         "the Quick take no longer names the best run")
        self.assertEqual(fn.count("${Math.round(s.runs).toLocaleString()} runs"), 1,
                         "a card row prints something other than RUNS (an area run counts a run, not its kills)")
        self.assertNotIn("${s.r50.toLocaleString()} runs", fn, "a card row prints kills for an area run as its runs")


RED_PROOF = [
    {"why": "v3886 (his 11-08 on Tyrael's Might) - the card sorts by time alone again",
     "file": "bible.html",
     "find": "  if (typeof window._qwRank === 'function') return window._qwRank(sources);\n",
     "replace": "  if (typeof window._qwRank === 'function') return sources.sort((a, b) => a.hrs - b.hrs);\n",
     "matches": 1, "needs": "node"},
    {"why": "v3886 - the Quick take calls the fewest-runs place the fastest",
     "file": "bible.html",
     "find": "Quick take @ ${window._oddsAtSay()}:</strong> Best run = <span",
     "replace": "Quick take @ ${window._oddsAtSay()}:</strong> Fastest = <span",
     "matches": 1},
    {"why": "v3886 - a card row prints kills-for-a-50%-chance as its runs (a 350-cow run reads as 350 runs)",
     "file": "bible.html",
     "find": "<div class=\"gic-source-stats\">${Math.round(s.runs).toLocaleString()} runs",
     "replace": "<div class=\"gic-source-stats\">${s.r50.toLocaleString()} runs",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
