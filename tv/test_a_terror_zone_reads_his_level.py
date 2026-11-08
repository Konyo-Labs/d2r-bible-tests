# -*- coding: utf-8 -*-
"""v3884 (REG-3437 + REG-3438, his rulings 11-08 ~11:50-12:00) - A TERROR ZONE'S ODDS ARE HIS LEVEL'S, AND A TZ RUN WEARS ITS TZ.

His words: "Add a level setting" (asked which level he farms terror zones at), and "for anything TZ to farm within the
quickwins or the best runs make sure to emphasize on it ... maybe color" / "i can TZ and shard myself ... sometimes i can TZ
sometimes i wont". MEASURED 11-08 against silospen's own API (Terror Zone ON, /players 1): Tyrael's Might from Hell TZ Diablo
is 1:178,086 at character level 0-90 and 1:19,551 at 94-99 (MF 400); Hell TZ Mephisto turns on at 91; Heaven's Light from NM TZ
Mephisto does not drop below level 64. The page stored ONE TZ figure per row (Hell at level 99) - GrokBot, reading the
dropcalc site at its default level 0, found "1:49,500 matches nothing" (#230 6720166936).

Now `tz-level-odds` (tv/silospen_tz_levels.py --build) carries, per farm / TZ column / item, the odds from each level where
they move past 2%, and a varying TZ cell of BOSSES reads its odds at the LVL slider's level each time it is asked (the
registry's source row reads its cell) - one place, every surface. Unset, every TZ figure is the level-99 one it always was.
Every TZ run's name wears a TZ tag in the terror colour (Quick wins rows, Best runs titles); plain runs do not.

Drives the page's own code in node: the level block (cut from bible.html) over the page's real BOSSES and table, and the
page's own effChance at MF 400 / MF 0 - held to silospen's printed figures. RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")

#: silospen's own answers, read 11-08 (dropcalc.php itemProbabilities / monsterProbabilities, D2R_ROW_3_0, Unique,
#: /players 1, party 1, Terror Zone ON at the level named). Not the page's numbers - the source the page must equal.
SILOSPEN = [
    # (farm, column, item, level, MF, 1:N)
    ("diablo", "hellTz", "Tyrael's Might", 90, 400, 178086),
    ("diablo", "hellTz", "Tyrael's Might", 94, 400, 19551),
    ("diablo", "hellTz", "Tyrael's Might", 99, 400, 19551),
    ("mephisto", "hellTz", "Tyrael's Might", 90, 400, 177636),
    ("mephisto", "hellTz", "Tyrael's Might", 93, 400, 19601),
    ("baal", "hellTz", "Tyrael's Might", 80, 400, 19644),
    ("baal", "hellTz", "Tyrael's Might", 99, 400, 19644),
    # GrokBot's acceptance checks (#230 6720166936), silospen at its own default Terror Zone Level 0, MF 400. Since v3885 a level
    # under 68 reads as 68 (his 11-08 "no one is farming below level 68") - and these three do not change between 1 and 68
    ("diablo", "hellTz", "Tyrael's Might", 1, 400, 178085),
    ("andariel", "hellTz", "Heaven's Light", 1, 400, 2527),
    ("baal", "nmTz", "Heaven's Light", 1, 400, 1691),
    # v3885 - NM TZ Mephisto cannot drop Heaven's Light below 64 (silospen), but nobody farms below 68: level 60 and level 1
    # read as 68, where silospen's pull (MF 300) gives 1:1,823 - within 2% of the stored 1:1,819, which the page shows
    ("mephisto", "nmTz", "Heaven's Light", 60, 300, 1823),
    ("mephisto", "nmTz", "Heaven's Light", 1, 300, 1823),
]
#: and where silospen gives NO row at that level (the page must say it does not drop, never the level-99 figure)
SILOSPEN_NONE = [("mephisto", "hellTz", "Tyrael's Might", 1)]


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


def _node(prog):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise AssertionError("node could not run the page's code - UNKNOWN, not passing: " + (r.stderr or r.stdout)[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _code(src):
    src = re.sub(r"/\*.{0,4000}?\*/", "", src, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", r"\1", ln) for ln in src.split("\n"))


@unittest.skipUnless(NODE, "node is required to drive the page's own level block and drop math")
class ATerrorZoneReadsHisLevel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        src = cls.src
        tab = re.search(r'<script type="application/json" id="tz-level-odds">(.*?)</script>', src, re.S).group(1)
        i = src.index("const BOSSES = [") + len("const BOSSES = ")
        bosses, _ = json.JSONDecoder().raw_decode(src[i:])
        block = _cut(src, "const TZ_LEVEL_ODDS = ", "const ITEM_REGISTRY = {};")
        engine = _cut(src, "const effMF = (gMF, factor) =>", "// GRAIL-FARM BRIDGE")
        cases = SILOSPEN + [c + (0, None) for c in SILOSPEN_NONE]
        prog = ("var window = {}; var TABLE = %s;\n"
                "var document = { getElementById: function(id){ return id === 'tz-level-odds' ? { textContent: TABLE } : null; } };\n"
                "var mf = 300, players = 1;\nvar BOSSES = %s;\nvar CASES = %s;\n"
                % (json.dumps(tab), json.dumps(bosses), json.dumps(cases))
                + block + "\n" + engine + "\n" + r"""
var out = { odds: [], unset: {}, getter: {} };
function row(farm, item){ var b = BOSSES.filter(function(x){ return x.id === farm; })[0];
  return b && b.dropTable.filter(function(d){ return d.n === item; })[0]; }
CASES.forEach(function(c){ var d = row(c[0], c[2]); _TZ_CHAR_LVL = c[3]; mf = c[4];
  var base = d ? d[c[1]] : undefined;
  out.odds.push([c[0], c[1], c[2], c[3], c[4], base == null ? null : effChance(base, c[0], c[1])]); });
_TZ_CHAR_LVL = null; mf = 300;
var tm = row('diablo', "Tyrael's Might"); out.unset.diabloTm = tm && tm.hellTz;
out.getter.diabloTm = !!(tm && Object.getOwnPropertyDescriptor(tm, 'hellTz').get);
var plain = row('diablo', "Tyrael's Might"); out.getter.plainHell = !!Object.getOwnPropertyDescriptor(plain, 'hell').get;
out.atLevel = [tzOddsAtLevel([[60, 0], [64, 29470], [68, 1823]], 777, null), tzOddsAtLevel([[60, 0], [64, 29470], [68, 1823]], 777, 61),
               tzOddsAtLevel([[60, 0], [64, 29470], [68, 1823]], 777, 66), tzOddsAtLevel([[60, 0], [64, 29470], [68, 1823]], 777, 99),
               tzOddsAtLevel([[60, 0], [64, 29470], [68, 1823]], 777, 40),
               tzOddsAtLevel([[1, 190886], [94, 20976]], 20975, null), tzOddsAtLevel([[1, 190886], [94, 20976]], 20975, 1)];
out.same = [tzOddsAtLevel([[68, 1823]], 1819, 90), tzOddsAtLevel([[68, 2000]], 1819, 90), tzOddsAtLevel([[68, 1823], [80, 0]], 1819, 85),
            tzOddsAtLevel([[68, 7137]], 6948, null)];
process.stdout.write(JSON.stringify(out));
""")
        cls.o = _node(prog)
        cls.bosses = bosses

    def test_his_level_moves_a_terror_zones_odds_as_silospen_does(self):
        """* THE POINT - Tyrael's Might from Hell TZ Diablo: 1:178,086 at level 90, 1:19,551 at 94 (silospen, MF 400)"""
        bad = []
        for farm, col, item, lvl, mf, page in self.o["odds"]:
            want = next((c[5] for c in SILOSPEN if c[:5] == (farm, col, item, lvl, mf)), "NONE")
            if want == "NONE":
                if page is not None:
                    bad.append("%s %s %s at level %d: page 1:%s - silospen has no row" % (farm, col, item, lvl, page))
            elif page is None or abs(page - want) / float(want) > 0.025:
                bad.append("%s %s %s at level %d MF %d: page 1:%s, silospen 1:%s" % (farm, col, item, lvl, mf, page, want))
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_unset_is_the_level_99_figure_it_always_was(self):
        st = re.search(r'\{"n":"Tyrael\'s Might"[^{}]*\}', self.src[self.src.index('{"id":"diablo"'):]).group(0)
        self.assertEqual(self.o["unset"]["diabloTm"], json.loads(st)["hellTz"],
                         "with no level set, a TZ figure is no longer the stored level-99 one")
        self.assertTrue(self.o["getter"]["diabloTm"], "the varying TZ cell does not read his level")
        self.assertFalse(self.o["getter"]["plainHell"], "a PLAIN (non-TZ) cell reads the level - the level is a terror zone's only")

    def test_the_breakpoint_reader(self):
        self.assertEqual(self.o["atLevel"], [1823, 1823, 1823, 1823, 1823, 20975, 190886],
                         "v3885: unset -> level 99; a level under 68 -> 68 (61, 66, 40 all read 68's 1:1,823); within 2% of the "
                         "stored figure -> the stored (20,976 -> 20,975)")

    def test_a_level_never_splits_what_silospen_calls_equal(self):
        """* his 11-08 - "its basically the same ... 0.2% difference ... its irrelevant data": within 2% the stored figure stands"""
        self.assertEqual(self.o["same"], [1819, 2000, None, 7137],
                         "1:1,823 vs 1:1,819 is the stored figure; 1:2,000 is 10% off and stands; 0 still means it does not "
                         "drop; a one-point 68+ row (a Normal TZ cell stored at level 50) is read even with no level set")

    def test_the_registry_row_reads_its_cell_and_the_slider_persists_per_account(self):
        code = _code(self.src)
        self.assertIn('if (_dsc && _dsc.get) Object.defineProperty(_src, "chance", { get(){ return d[k]; }, enumerable: true, configurable: true });',
                      code, "a source row keeps the level-99 figure it was built with - the cards and Quick wins never move")
        self.assertIn('<input type="range" id="clvl" min="68" max="99" step="1" value="99"', self.src)   # v3885: 68 and up
        self.assertIn("window.LSR.setItem('d2r_charLevel', String(_TZ_CHAR_LVL))", code)
        self.assertIn('"d2r_mf", "d2r_players", "d2r_charLevel",', code, "the level is not forked per account like MF and /players")

    def test_a_tz_run_wears_its_tz_and_a_plain_run_does_not(self):
        fn = _cut(self.src, "  function _tzLabelHtml(label){", "  window._tzLabelHtml = _tzLabelHtml;")
        o = _node("var window = {};\nfunction esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;')"
                  ".replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n" + fn
                  + "\nprocess.stdout.write(JSON.stringify([_tzLabelHtml('NM TZ Mephisto'), _tzLabelHtml('Hell Mephisto'),"
                    " _tzLabelHtml('Hell TZ The Pit')]));")
        self.assertIn('NM <span class="tz-tag" title="', o[0], "a TZ run's name carries no TZ tag: %r" % o[0])
        self.assertIn('">TZ</span> Mephisto', o[0])
        self.assertEqual(o[1], "Hell Mephisto", "a plain run grew a tag")
        self.assertIn('">TZ</span> The Pit', o[2])
        code = _code(self.src)
        self.assertIn("'>' + _tzLabelHtml(p.label) + '</b>'", code, "Quick wins rows print the plain name")
        self.assertIn("Run <b class=\"f-rwbig\">'+_tzLabelHtml(r.boss)+'</b>", code, "Best runs titles print the plain name")
        self.assertIn(":is(#tab-funi,#tab-fsets) .tz-tag{display:inline-block;", code)
        self.assertIn("color:var(--terror);", code[code.index(":is(#tab-funi,#tab-fsets) .tz-tag{"):][:400],
                      "the tag is not in the page's terror colour")


RED_PROOF = [
    {"why": "v3884 (REG-3437) - a TZ cell keeps the level-99 figure whatever his level (Tyrael's Might from Hell TZ Diablo 1:19,551 at 90)",
     "file": "bible.html",
     "find": "      Object.defineProperty(d, k, { get(){ return tzOddsAtLevel(pts, base, _TZ_CHAR_LVL); }, enumerable: true, configurable: true });\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "v3884 (REG-3437) - a level where it does not drop reads the stored figure instead of 'does not drop'",
     "file": "bible.html",
     "find": "  if (!(n > 0)) return null;                              // 0 = it does not drop at this level\n",
     "replace": "  if (!(n > 0)) return base;\n", "matches": 1, "needs": "node"},
    {"why": "v3884 (REG-3437) - unset reads level 1, not the level-99 figure",
     "file": "bible.html",
     "find": "  lvl = (lvl == null) ? 99 : Math.max(TZ_LVL_FLOOR, lvl);  // unset = 99, the level the Hell TZ figures were stored at\n",
     "replace": "  lvl = (lvl == null) ? 1 : Math.max(TZ_LVL_FLOOR, lvl);\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (his 11-08 'no one is farming below level 68') - a level under 68 reads as itself again",
     "file": "bible.html",
     "find": "  lvl = (lvl == null) ? 99 : Math.max(TZ_LVL_FLOOR, lvl);  // unset = 99, the level the Hell TZ figures were stored at\n",
     "replace": "  lvl = (lvl == null) ? 99 : lvl;\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (his 11-08 '0.2% difference ... irrelevant data') - a figure within 2% of the stored one splits two runs again",
     "file": "bible.html",
     "find": "  return (base > 0 && Math.abs(n - base) <= TZ_SAME * base) ? base : n;   // within 2%: the stored figure (his ruling)\n",
     "replace": "  return n;\n", "matches": 1, "needs": "node"},
    {"why": "v3884 (REG-3437) - the registry's source row keeps its build-time figure (no surface follows the level)",
     "file": "bible.html",
     "find": '        if (_dsc && _dsc.get) Object.defineProperty(_src, "chance", { get(){ return d[k]; }, enumerable: true, configurable: true });   // v3884 (REG-3437) - his level\n',
     "replace": "", "matches": 1},
    {"why": "v3884 (REG-3438) - a TZ run's name is printed plain again",
     "file": "bible.html",
     "find": "    return t.replace(/(^|\\s)TZ(\\s|$)/, '$1<span class=\"tz-tag\" title=\"' + esc(tip) + '\">TZ</span>$2');\n",
     "replace": "    return t;\n", "matches": 1, "needs": "node"},
    {"why": "v3884 (REG-3438) - Best runs titles lose the tag",
     "file": "bible.html",
     "find": "Run <b class=\"f-rwbig\">'+_tzLabelHtml(r.boss)+'</b>",
     "replace": "Run <b class=\"f-rwbig\">'+esc(r.boss)+'</b>", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
