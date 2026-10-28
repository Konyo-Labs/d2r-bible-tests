# -*- coding: utf-8 -*-
"""The Edit tab states the odds of the mods he picked.

SPEC_174 §10, under the picked mods: the chance of those mods, the chance of the
typed floors or higher, and the disclaimer that base and quality are not in the
figure. Magic uses the public mix — a prefix on half of magic items, a suffix on
three quarters, both on a quarter — times this row's frequency over the whole
eligible pool of that kind. A blank range does not divide the value line. A typed
floor keeps the inclusive share of its range at or above it.

A rare draw, a crafted draw, an automod and a superior row are not pinned. Those print
UNKNOWN. A chosen class IS a pinned draw, so its mod odds print; only its value line is
UNKNOWN, because a class has no order to be at or above (the second eye on 0a7ab41c caught
this prose saying the whole of it was UNKNOWN while the painter and this law said otherwise). No mods picked prints nothing: a 1/1 is not a measurement.

The ratios are recomputed from this install's tables on each run. Nothing here is 1/490.
Drives the shipped builder. A missing node raises. This law does not skip.
"""
import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_the_character_builder_is_their_builder as CB  # noqa: E402

HELP = r"""
function mk(cls, lvl){ window.openCharBuilder(); window._cbOpenNew(); window._cbNewCls(cls); window._cbNewLvl(lvl); window._cbNewGo(); }
function cur(){ return window._cbAll()[window._cbState().bid]; }
function entry(){ var inv = cur().sets[0].inv; return inv[inv.length - 1]; }
function ids(list){ return (list || []).map(function(a){ return a[0]; }); }
function gcd(a, b){ a = Math.abs(a); b = Math.abs(b); while (b){ var t = a % b; a = b; b = t; } return a || 1; }
function red(n, d){ var g = gcd(n, d); return [n / g, d / g]; }
function weight(list, id){
  var hit = null, sum = 0;
  list.forEach(function(a){ sum += a[12] | 0; if (a[0] === id) hit = a[12] | 0; });
  return { hit: hit, sum: sum };
}
function oddsText(){
  var h = MODAL._html, i = h.indexOf('id="cb-odds"');
  if (i < 0) return '';
  return h.slice(h.indexOf('>', i) + 1, h.indexOf('</div>', i));
}
function span(r){
  if (!r || r[0] === 'C') return null;
  var lo, hi, key = r[2];
  if (r[0] === 'L'){ lo = Math.min(r[1], r[3] == null ? r[1] : r[3]); hi = Math.max(r[1], r[3] == null ? r[1] : r[3]); }
  else if (typeof r[0] === 'number' && typeof r[1] === 'number'){ lo = Math.min(r[0], r[1]); hi = Math.max(r[0], r[1]); }
  else return null;
  return { key: key, lo: lo, hi: hi, kind: r[0] === 'L' ? 'L' : 'n' };
}
"""

DISC = "These odds do not factor in getting the desired base or quality to drop."


def _run(body):
    if CB.NODE is None:
        raise AssertionError("node is not on this machine — this gate does not skip")
    return CB._run(HELP + body)


def _bit(pair):
    n, d = pair
    tenths = int(math.floor(n * 1000 / d + 0.5))
    return "%d/%d (%d.%d%%)" % (n, d, tenths // 10, tenths % 10)


class TheEditTabStatesTheOddsOfTheModsHePicked(unittest.TestCase):

    def test_a_magic_prefix_is_half_its_weight_and_a_pair_is_a_quarter(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3');
          var e = entry();
          var S = window._cbSpawnPool(e), P = window._cbAffixPool(e);
          OUT.base = window._cbDb().b[e.base][0];
          OUT.same = ['p', 's', 'a'].map(function(k){ return ids(S[k]).join('|') === ids(P.rows[k]).join('|'); });
          OUT.n = { p: S.p.length, s: S.s.length, a: S.a.length };
          OUT.zero = ['p', 's', 'a'].reduce(function(n, k){ return n + S[k].filter(function(a){ return !a[12]; }).length; }, 0);
          OUT.before = MODAL._html.indexOf('id="cb-odds"');
          var bare = window._cbAffixOdds(e);
          OUT.bare = bare;
          var wp = weight(S.p, 'p700'), ws = weight(S.s, 's338');
          OUT.wp = wp; OUT.ws = ws;
          OUT.addedP = window._cbAddMod('p700');
          e = entry();
          var S2 = window._cbSpawnPool(e), P2 = window._cbAffixPool(e);
          OUT.held = { spawn: S2.p.length, ui: P2.rows.p.length, inSpawn: ids(S2.p).indexOf('p700') >= 0 };
          OUT.pre = window._cbAffixOdds(e);
          OUT.wantPre = red(wp.hit, 2 * wp.sum);
          OUT.addedS = window._cbAddMod('s338');
          e = entry();
          OUT.both = window._cbAffixOdds(e);
          OUT.wantBoth = red(wp.hit * ws.hit, 4 * wp.sum * ws.sum);
          OUT.text = oddsText();
          OUT.order = (function(){
            var h = MODAL._html;
            var row = h.indexOf('class="cb-mod"'), odds = h.indexOf('id="cb-odds"'), add = h.indexOf('class="cb-add"');
            return row >= 0 && odds > row && add > odds;
          })();
          window._cbDelMod(0);
          e = entry();
          OUT.suf = window._cbAffixOdds(e);
          OUT.wantSuf = red(3 * ws.hit, 4 * ws.sum);
          OUT.two = (function(){
            var row = { id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: 'p700', rolls: {} }, { id: S.p[0][0] === 'p700' ? S.p[1][0] : S.p[0][0], rolls: {} }] };
            return window._cbAffixOdds(row);
          })();
        """)
        self.assertIn("Charm", out["base"])
        self.assertEqual(out["same"], [True, True, True], "an empty item's generation pool and ADD MOD list disagree")
        self.assertGreater(out["n"]["p"], 1)
        self.assertGreater(out["n"]["s"], 1)
        self.assertEqual(out["zero"], 0, "a frequency-0 row is in the generation pool")
        self.assertLess(out["before"], 0, "odds are painted before any mod is picked")
        self.assertIsNone(out["bare"])
        self.assertTrue(out["wp"]["hit"] and out["wp"]["sum"])
        self.assertTrue(out["ws"]["hit"] and out["ws"]["sum"])
        self.assertTrue(out["addedP"] and out["addedS"])
        self.assertEqual(out["held"]["spawn"], out["n"]["p"], "picking a prefix dropped it out of the generation pool")
        self.assertEqual(out["held"]["ui"], 0, "a full magic prefix slot is still offered")
        self.assertTrue(out["held"]["inSpawn"])
        self.assertEqual(out["pre"]["mods"], out["wantPre"], "a lone prefix is not half its weight")
        self.assertEqual(out["pre"]["values"], out["wantPre"], "a fixed roll divided the value line")
        self.assertTrue(out["pre"]["known"])
        self.assertEqual(out["both"]["mods"], out["wantBoth"], "a prefix and a suffix are not a quarter of the product")
        self.assertEqual(out["both"]["values"], out["wantBoth"], "blank ranges divided the value line")
        self.assertIn(_bit(out["wantBoth"]), out["text"])
        self.assertIn("Odds of rolling selected values or higher: " + _bit(out["wantBoth"]), out["text"])
        self.assertIn(DISC, out["text"])
        self.assertTrue(out["order"], "the odds line is not under the picked mods and above Add Mod")
        self.assertEqual(out["suf"]["mods"], out["wantSuf"], "a lone suffix is not three quarters of its weight")
        self.assertFalse(out["two"]["known"])
        self.assertIn("one prefix and one suffix", out["two"]["why"])

    def test_a_typed_floor_keeps_the_share_at_or_above_it(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3');
          window._cbAddMod('p700'); window._cbAddMod('s338');
          var vita = window._cbAf('s338'), roll = null;
          (vita[11] || []).forEach(function(ln){ (ln[1] || []).forEach(function(r){ if (!roll) roll = span(r); }); });
          OUT.roll = roll;
          var e = entry(), both = window._cbAffixOdds(e);
          function put(v){
            window._cbCommit(function(b){
              var inv = b.sets[0].inv, x = inv[inv.length - 1].affixes[1];
              x.rolls = x.rolls || {};
              if (v == null) delete x.rolls[roll.key]; else x.rolls[roll.key] = v;
            });
            window._cbModal();
            return { odds: window._cbAffixOdds(entry()), text: oddsText() };
          }
          OUT.blank = put(null);
          OUT.top = put(roll.hi);
          OUT.floor = put(roll.lo);
          OUT.mid = put(roll.lo + 1);
          OUT.out = put(roll.hi + 50);
          OUT.mods = both.mods;
          /* The charm and the diadem's own pools have no ranged per-level affix. of Vita's own
             36-40, rewritten into the page's ["L", lo, key, hi, shift] shape, is the same bounds:
             the value line must use those bounds and not the level-scaled display. */
          var saved = vita[11];
          vita[11] = [[0, [['L', roll.lo, roll.key, roll.hi, 3]], null, 'hp']];
          var asL = { id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: 'p700', rolls: {} }, { id: 's338', rolls: {} }] };
          var asLTop = { id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: 'p700', rolls: {} }, { id: 's338', rolls: {} }] };
          asLTop.affixes[1].rolls[roll.key] = roll.hi;
          OUT.levelBlank = window._cbAffixOdds(asL);
          OUT.levelTop = window._cbAffixOdds(asLTop);
          vita[11] = [[0, [['L', roll.lo, roll.key, roll.lo, 3]], null, 'hp']];
          var asLFixed = { id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: 'p700', rolls: {} }, { id: 's338', rolls: { } }] };
          asLFixed.affixes[1].rolls[roll.key] = roll.lo;
          OUT.levelFixed = window._cbAffixOdds(asLFixed);
          vita[11] = [[0, [['C', 0, 'm1', 7]], null, 'class']];
          var chosen = { id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: 's338', rolls: { m1: 0 } }] };
          var blankC = { id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: 's338', rolls: {} }] };
          OUT.chosen = window._cbAffixOdds(chosen);
          OUT.blankC = window._cbAffixOdds(blankC);
          vita[11] = saved;
          OUT.restored = window._cbAf('s338')[11] === saved;
        """)
        roll = out["roll"]
        self.assertIsNotNone(roll)
        self.assertNotEqual(roll["lo"], roll["hi"])
        self.assertEqual(roll["kind"], "n")
        mods = out["mods"]
        width = roll["hi"] - roll["lo"] + 1
        self.assertGreater(width, 1)
        self.assertEqual(out["blank"]["odds"]["values"], mods)
        self.assertIn(_bit(mods), out["blank"]["text"])
        top = [mods[0], mods[1] * width]
        g = math.gcd(top[0], top[1])
        top = [top[0] // g, top[1] // g]
        self.assertEqual(out["top"]["odds"]["values"], top, "the top of the range did not keep 1 of %d" % width)
        self.assertEqual(out["top"]["odds"]["mods"], mods, "a typed floor moved the mods line")
        self.assertIn(_bit(top), out["top"]["text"])
        self.assertEqual(out["floor"]["odds"]["values"], mods, "typing the bottom of the range shrank a line that still covers every value")
        mid_n = roll["hi"] - (roll["lo"] + 1) + 1
        mid = [mods[0] * mid_n, mods[1] * width]
        g = math.gcd(mid[0], mid[1])
        mid = [mid[0] // g, mid[1] // g]
        self.assertEqual(out["mid"]["odds"]["values"], mid)
        self.assertTrue(out["out"]["odds"]["known"])
        self.assertEqual(out["out"]["odds"]["mods"], mods)
        self.assertIsNone(out["out"]["odds"]["values"])
        self.assertIn("outside the table range", out["out"]["odds"]["valuesWhy"])
        self.assertIn("UNKNOWN", out["out"]["text"])
        self.assertNotIn(_bit(top), out["out"]["text"])
        self.assertEqual(out["levelBlank"]["mods"], mods, "rewriting the line as per-level moved the mods odds")
        self.assertEqual(out["levelBlank"]["values"], mods, "a blank per-level range divided the value line")
        self.assertEqual(out["levelTop"]["mods"], mods)
        self.assertEqual(out["levelTop"]["values"], top, "a per-level floor did not use the table bounds")
        self.assertEqual(out["levelFixed"]["values"], out["levelFixed"]["mods"], "a fixed per-level roll divided the value line")
        self.assertTrue(out["chosen"]["known"])
        self.assertIsNone(out["chosen"]["values"])
        self.assertIn("chosen class", out["chosen"]["valuesWhy"])
        self.assertEqual(out["blankC"]["values"], out["blankC"]["mods"])
        self.assertTrue(out["restored"])

    def test_an_unpinned_draw_stays_unknown(self):
        out = _run(r"""
          mk('Warlock', 90);
          window._cbOpenPick('slot', 'head'); window._cbChoose('b:ci3');
          window._cbQuality('rare');
          var e = cur().sets[0].slots.head, P = window._cbAffixPool(e);
          OUT.rareAdded = P.rows.p.length ? window._cbAddMod(P.rows.p[0][0]) : false;
          OUT.rare = window._cbAffixOdds(cur().sets[0].slots.head);
          OUT.rareText = oddsText();
          window._cbQuality('sup');
          e = cur().sets[0].slots.head;
          P = window._cbAffixPool(e);
          OUT.supN = P.rows.q.length;
          OUT.supAdded = P.rows.q.length ? window._cbAddMod(P.rows.q[0][0]) : false;
          OUT.sup = window._cbAffixOdds(cur().sets[0].slots.head);
          OUT.supText = oddsText();
          var d = window._cbDb(), auto = null, supOnMagic = null;
          Object.keys(d.b).some(function(code){
            if (auto && supOnMagic) return true;
            if (!d.b[code][20]) return false;
            var row = { id: 'b:' + code, base: code, q: 'm', ilvl: 99, affixes: [] };
            var pool = window._cbSpawnPool(row);
            if (!auto && pool.a.length){
              row.affixes = [{ id: 'p700', rolls: {} }, { id: pool.a[0][0], rolls: {} }];
              var pref = pool.p[0];
              if (pref) row.affixes[0] = { id: pref[0], rolls: {} };
              auto = { code: code, odds: window._cbAffixOdds(row) };
            }
            return false;
          });
          var supId = (d.qm && d.qm.sup && d.qm.sup[0]) ? d.qm.sup[0][0] : null;
          if (supId){
            supOnMagic = window._cbAffixOdds({ id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: supId, rolls: {} }] });
          }
          OUT.auto = auto;
          OUT.supOnMagic = supOnMagic;
          OUT.craft = window._cbAffixOdds({ id: 'c88', base: 'amu', q: 'c', ilvl: 99, affixes: [{ id: 's174', rolls: {} }] });
          OUT.low = window._cbAffixOdds({ id: 'b:ci3', base: 'ci3', q: 'low', ilvl: 99, affixes: [{ id: 'p700', rolls: {} }] });
          OUT.gone = window._cbAffixOdds({ id: 'b:cm3', base: 'cm3', q: 'm', ilvl: 99, affixes: [{ id: 'no-such-affix', rolls: {} }] });
        """)
        self.assertTrue(out["rareAdded"])
        self.assertFalse(out["rare"]["known"])
        self.assertIn("rare", out["rare"]["why"])
        self.assertIn("not pinned", out["rare"]["why"])
        self.assertIn("UNKNOWN", out["rareText"])
        self.assertIn(DISC, out["rareText"])
        self.assertNotRegex(out["rareText"], r"\d+/\d+")
        self.assertGreater(out["supN"], 0, "a diadem has no superior row")
        self.assertTrue(out["supAdded"])
        self.assertFalse(out["sup"]["known"])
        self.assertIn("no table frequency", out["sup"]["why"])
        self.assertNotRegex(out["supText"], r"\d+/\d+")
        auto = out["auto"]
        self.assertIsNotNone(auto, "no spawnable base has an automod at item level 99")
        self.assertFalse(auto["odds"]["known"])
        self.assertIn("automod", auto["odds"]["why"])
        self.assertNotIn("mods", auto["odds"])
        sup = out["supOnMagic"]
        self.assertIsNotNone(sup)
        self.assertFalse(sup["known"])
        self.assertIn("no table frequency", sup["why"])
        self.assertFalse(out["craft"]["known"])
        self.assertIn("crafted", out["craft"]["why"])
        self.assertFalse(out["low"]["known"])
        self.assertNotIn("mods", out["low"])
        self.assertFalse(out["gone"]["known"])
        self.assertIn("not in the tables", out["gone"]["why"])

RED_PROOF = [
    {"why": "a lone magic prefix is printed at its whole weight, not half of it",
     "file": "bible.html",
     "find": "    else if (pp) rat = _cbRatMul(_cbRatMul(rat, 1, 2), pp.hit, pp.sum);\n",
     "replace": "    else if (pp) rat = _cbRatMul(rat, pp.hit, pp.sum);\n",
     "matches": 1, "needs": "node"},
    {"why": "a prefix and a suffix together are printed at half the product, not the quarter magic rolls both",
     "file": "bible.html",
     "find": "    if (pp && ss) rat = _cbRatMul(_cbRatMul(_cbRatMul(rat, 1, 4), pp.hit, pp.sum), ss.hit, ss.sum);\n",
     "replace": "    if (pp && ss) rat = _cbRatMul(_cbRatMul(_cbRatMul(rat, 1, 2), pp.hit, pp.sum), ss.hit, ss.sum);\n",
     "matches": 1, "needs": "node"},
    {"why": "a lone suffix is printed at half its weight, not the three quarters magic rolls one",
     "file": "bible.html",
     "find": "    else rat = _cbRatMul(_cbRatMul(rat, 3, 4), ss.hit, ss.sum);\n",
     "replace": "    else rat = _cbRatMul(_cbRatMul(rat, 1, 2), ss.hit, ss.sum);\n",
     "matches": 1, "needs": "node"},
    {"why": "a typed floor keeps the share strictly above it, so the top of the range reads as impossible",
     "file": "bible.html",
     "find": "          values = _cbRatMul(values, hi - typed + 1, hi - lo + 1);\n",
     "replace": "          values = _cbRatMul(values, hi - typed, hi - lo + 1);\n",
     "matches": 1, "needs": "node"},
    {"why": "a blank range divides the value line as if a floor had been typed",
     "file": "bible.html",
     "find": "          if (typed == null || typed === '') return;\n",
     "replace": "          if (typed == null || typed === '') { if (lo !== hi) values = _cbRatMul(values, 1, hi - lo + 1); return; }\n",
     "matches": 1, "needs": "node"},
    {"why": "a typed roll beyond the table range is folded into the fraction instead of read as UNKNOWN",
     "file": "bible.html",
     "find": "          if (typeof typed !== 'number' || typed < lo || typed > hi){ valuesWhy = 'a typed roll is outside the table range'; return; }\n",
     "replace": "          if (typeof typed !== 'number'){ valuesWhy = 'a typed roll is outside the table range'; return; }\n",
     "matches": 1, "needs": "node"},
    {"why": "a chosen class prints a value line though a class has no order to be at or above",
     "file": "bible.html",
     "find": "          if (kind === 'C'){ valuesWhy = 'a chosen class has no pinned order to be at or above'; return; }\n",
     "replace": "          if (kind === 'C'){ return; }\n",
     "matches": 1, "needs": "node"},
    {"why": "a rare item's unpinned 3-to-6 draw loses the reason it is UNKNOWN",
     "file": "bible.html",
     "find": "    if (q === 'rare') return { known: false, why: 'a rare item draws 3 to 6 affixes and that draw is not pinned' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "a crafted item's draw loses the reason it is UNKNOWN",
     "file": "bible.html",
     "find": "    if (q === 'c') return { known: false, why: 'a crafted item draws like a rare, and its fixed craft affixes are not in this frequency pool' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "a superior item is not named as stored with no table frequency",
     "file": "bible.html",
     "find": "    if (q === 'sup') return { known: false, why: 'a superior row is stored with no table frequency' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "an automod is divided as if it were a pinned magic draw",
     "file": "bible.html",
     "find": "    if (kinds.a.length) return { known: false, why: 'an automod is not pinned as a draw this page can divide' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "an affix missing from the tables is not named as missing",
     "file": "bible.html",
     "find": "    if (missing) return { known: false, why: 'an affix on this item is not in the tables' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "an item with no mods picked prints 1/1, which is not a measurement",
     "file": "bible.html",
     "find": "    if (!ax.length) return null;\n    var it = e && _cbItem(e.id), d = _cbDb(), b = d && e && d.b[e.base];\n",
     "replace": "    if (!ax.length) return { known: true, mods: [1, 1], values: [1, 1], valuesWhy: null };\n    var it = e && _cbItem(e.id), d = _cbDb(), b = d && e && d.b[e.base];\n",
     "matches": 1, "needs": "node"},
    {"why": "the odds line drops the disclaimer that base and quality are not in the figure",
     "file": "bible.html",
     "find": "    var disc = 'These odds do not factor in getting the desired base or quality to drop.';\n",
     "replace": "    var disc = '';\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
