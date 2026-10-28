# -*- coding: utf-8 -*-
"""#63 (REG-2503, REG-2508) - A GOOD MF NEVER TURNS 1:N ODDS INTO A PERCENT, AN EVENT DROP IS A PROBABILITY, AND THE
MF CURVE IS THE GAME'S.

One number carried two units and its SIZE decided which: a chance at or below EVENT_PCT_MAX (50) was an event
percent, anything above was 1:N odds. That holds for raw data only if no real 1:N is ever 50 or better - and the
drop math reads ADJUSTED values. On the code as it shipped, Nagelring from Normal Andariel (raw 1:79):
  * at his MF 699 /players 1 it adjusted to 1:70, and renderDetail kept only adjustedChance >= 100, so the item's
    best source fell out of its own ranking;
  * at MF 1000 /players 8 it adjusted to 1:49 and fmt printed "49%";
  * effChance skipped /players for any MF-adjusted value <= 50; runsFor / hoursFor / runHoursFor answered null.
And the silospen pull had already put REAL odds under 50 in the raw rows (Isenhart's Case 1:32 from Normal
Mephisto), which printed as percents too. Meanwhile the four real events were stored as 12 / 36 / 36 / 42 on every
difficulty although the keys drop on Hell only and Diablo Clone always drops Annihilus.

THE RULE NOW (isEventP, beside hoursFor): an event drop is held as a PROBABILITY in (0,1], every other chance as
ODDS >= 1. They meet only at exactly 1, where 1:1 and 100% are the same quantity, so "<= 1 is a probability" cannot
misread a 1:N however far MF and /players push it. An event drop is not timed and adds no rate; its per-run chance
is p itself. Keys sit on Hell only and print their card's sourced band; Annihilus is 100% (vanilla D2R, labelled).

THE 1:70 WAS ITSELF WRONG (REG-2508). His note was "i see it not 66 i se 70": the screen said 1:70 where the game
says 1:66. effMF read (MF x 100) / (MF + 250) - the game's curve divided by 2.5 - while the MF card on the same page
states MF x 250 / (MF + 250) ("699% = 184% effective"); the dock printed "eff unique: 73.66%". The first version of
this law re-typed the code's own formula and pinned (70, 49) as a "premise", so it would have gone red on the fix.
The expected figures are now the SOURCE's: silospen's calculator, the one every stored 1:N comes from, queried live
on 2026-10-22 (dropcalc.php?type=monsterProbabilities&version=D2R_ROW_3_0&itemQuality=UNIQUE&players=1&party=1 and
type=atomicTcProbabilities for the keys) - see SILOSPEN below. The page's curve must reproduce them.

What this law does NOT certify: the /players factor. That is test_players_moves_odds_by_silospens_own_factor (REG-2953,
which closed REG-2509: effChance now divides by silospen's own measured factor, PLAYER_F). Here /players is checked for
its UNIT (a 1:N stays a 1:N and still ranks), for being applied at all, and - one figure - that Nagelring at MF 1000
/players 8 is silospen's 1:35, read from the vendored pull (tv/data/silospen_players_rotw30.json).

Driven in node over code CUT from bible.html between its own boundaries: the drop engine (effMF .. fmtHours), the
BOSSES table, SPECIAL_DROPS, and renderDetail itself with a stub panel, so the ranking is read from the HTML it
paints.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
NODE = shutil.which("node")
EVENTS = {("summoner", "Key of Hate"), ("countess", "Key of Terror"), ("nihl", "Key of Destruction"),
          ("dclone", "Annihilus")}
DIFFS = ("norm", "normTz", "nm", "nmTz", "hell", "hellTz")


def _read():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end, inclusive=False):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + (len(end) if inclusive else 0)]


def _bosses(src):
    line = next(ln for ln in src.split("\n") if ln.startswith("const BOSSES = "))
    body = line[len("const BOSSES = "):]
    return json.loads(body[:body.rindex("];") + 1])


def _node(prog):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


# silospen RotW 3.0, measured 2026-10-22 (UNIQUE, /players 1, party 1): (item, boss, stored base at MF 300) -> {MF: N}
SILOSPEN = {
    ("Nagelring", "Normal Andariel", 79): {0: 186, 300: 79, 699: 66, 1000: 62},
    ("Crushflange", "Normal Andariel", 84): {0: 199, 300: 84, 699: 70, 1000: 66},
    ("Harlequin Crest", "Hell Mephisto", 836): {0: 1974, 300: 836, 699: 695},
}
# silospen RotW 3.0 atomic TC, Hell, party 1, decimal mode: /players 1-2, 3-4, 5-6, 7-8
KEY_SILOSPEN = {
    "Key of Terror": (0.07139835223, 0.09084617514, 0.0960792032, 0.09796001985),
    "Key of Hate": (0.0861533746, 0.11614571239, 0.12483359662, 0.12802530147),
    "Key of Destruction": (0.07932346012, 0.10407137931, 0.11099506033, 0.11351206024),
}
KEY_BAND_LABEL = "silospen RotW 3.0, /players 1-8"


def _band(ps):
    lo, hi = min(ps) * 100, max(ps) * 100
    return "%.1f-%.1f%%" % (math.floor(lo * 10 + 0.5) / 10, math.floor(hi * 10 + 0.5) / 10)


def _adjust(base, mf):
    """The game's curve (uniques factor 250, the stored base read at MF 300) - the one the page's MF card states."""
    eff = lambda g: (g * 250.0) / (g + 250.0)
    return max(1, int(math.floor(base * (1 + eff(300) / 100.0) / (1 + eff(mf) / 100.0) + 0.5)))


def _player_mult(f, players):
    """The page's own /players factor (PLAYER_F[boss][tier], index 0-7 = /players 1-8)."""
    return f[players - 1]


def _silospen_mf(item, mf, players):
    """silospen's 1:N at this MF and /players, from the vendored pull (REG-2953)."""
    with open(os.path.join(HERE, "data", "silospen_players_rotw30.json"), encoding="utf-8") as fh:
        at = json.load(fh)["mf"]["at"]
    return int(math.floor(1.0 / at[str(mf)][str(players)][item] + 0.5))


SCENARIO = r"""
var out = {};
function at(m, p){ mf = m; players = p; }
at(699, 1);
out.nag699 = effChance(79, 'andariel', 'norm');
out.nag699fmt = fmt(out.nag699);
out.nag699hours = hoursFor(out.nag699, 0.5, 90, killsPerRun('andariel'));
out.nag699runs = runsFor(out.nag699, 0.5);
at(1000, 8);
out.nag1000 = effChance(79, 'andariel', 'norm');
out.nag1000fmt = fmt(out.nag1000);
out.nag1000hours = hoursFor(out.nag1000, 0.5, 90, killsPerRun('andariel'));
out.nag1000runHours = runHoursFor([{ chance: out.nag1000, bossId: 'andariel', kph: 90 }]);
out.isen1000 = effChance(32, 'mephisto', 'norm');
out.isenRawFmt = fmt(32);
out.isenHours = hoursFor(32, 0.5, 60, 1);
out.anniFmt = fmt(1);
out.anniEff = effChance(1, 'dclone', 'hell');
out.anniHours = hoursFor(1, 0.5, 3, 1);
out.anniRuns = runsFor(1, 0.5);
out.anniPerRun = perRunChance(1, 'dclone');
out.anniRate = findRate(1, 'dclone', 3);
out.keyEff = effChance(0.0862, 'summoner', 'hell');
out.keyAdj = adjustChance(0.0862, 1000);
out.keyPerRun = perRunChance(0.0862, 'summoner');
out.keyHours = hoursFor(0.0862, 0.5, 85, 1);
out.keyRunHours = runHoursFor([{ chance: 0.0862, bossId: 'summoner', kph: 85 }]);
out.keyFmt = fmtDrop(0.0862, 'Key of Hate');
out.terrorFmt = fmtDrop(0.0714, 'Key of Terror');
out.destFmt = fmtDrop(0.0793, 'Key of Destruction');
out.anniDrop = fmtDrop(1, 'Annihilus');
out.oddsDrop = fmtDrop(49, 'Nagelring');
out.cards = SPECIAL_DROPS.key.items.map(function(x){ return [x.n, x.rate]; });
out.keyNote = SPECIAL_DROPS.key.important;
out.curve = {};
[[79, 0], [79, 300], [79, 699], [79, 1000], [84, 0], [84, 699], [84, 1000], [836, 0], [836, 699]].forEach(function(p){
  out.curve[p[0] + '@' + p[1]] = adjustChance(p[0], p[1]);
});
out.eff699 = effMF(699, 250).toFixed(2);
// the item ranking, read from the HTML renderDetail paints
var PANEL = { _h: '', classList: { add: function(){}, remove: function(){} } };
Object.defineProperty(PANEL, 'innerHTML', { get: function(){ return this._h; }, set: function(v){ this._h = String(v); } });
function $(id){ return id === 'item-detail' ? PANEL : null; }
function renderAidCard(){ return ''; }
function renderCodexCard(){ return ''; }
var wishlist = new Set();
function _gFound(){ return false; }
var ITEMS = [{ n: 'Nagelring', tc: 9, qlvl: 7, tier: 'common',
               sources: [{ boss: 'Normal Andariel', chance: 79, bossId: 'andariel', verified: false, kph: 90, diffKey: 'norm' }] },
             { n: 'Key of Hate', tc: 0, qlvl: 0, tier: 'special',
               sources: [{ boss: 'Hell The Summoner', chance: 0.0862, bossId: 'summoner', verified: false, kph: 85, diffKey: 'hell' }] }];
var selectedItem = 'Nagelring';
at(699, 1); renderDetail(); out.detail699 = PANEL._h;
at(1000, 8); renderDetail(); out.detail1000 = PANEL._h;
selectedItem = 'Key of Hate'; at(699, 1); renderDetail(); out.detailKey = PANEL._h;
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to drive the page's own drop math")
class AGoodMfNeverTurnsOddsIntoAPercent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        cls.bosses = _bosses(cls.src)
        engine = _cut(cls.src, "const effMF = (gMF, factor) =>", "// GRAIL-FARM BRIDGE")
        special = _cut(cls.src, "const SPECIAL_DROPS = {", "\n};", inclusive=True)
        detail = _cut(cls.src, "function renderDetail() {", "\nlet activeSourceKey = null;")
        spark = _cut(cls.src, "function sparkline(chance, kph, hoursMax) {", "\n}\n", inclusive=True)
        prelude = "var window = {}; var document = { getElementById: function(){ return null; } };\nvar mf = 300, players = 1;\n"
        cls.o = _node(prelude + special + "\n" + engine + "\n" + spark + "\n" + detail + "\n" + SCENARIO)
        f = re.search(r'const PLAYER_F = (\{.*?\});\n', cls.src)
        cls.player_f = json.loads(f.group(1))

    def test_the_raw_data_holds_one_unit_per_kind_of_drop(self):
        events, odds_under_50 = [], []
        for b in self.bosses:
            for d in b["dropTable"]:
                for k in DIFFS:
                    v = d.get(k)
                    if v is None:
                        continue
                    if (b["id"], d["n"]) in EVENTS:
                        self.assertTrue(0 < v <= 1, "%s %s %s holds %r - an event drop is a probability in (0,1]"
                                        % (b["id"], d["n"], k, v))
                        events.append((b["id"], d["n"], k))
                    else:
                        self.assertGreaterEqual(v, 1, "%s %s %s holds %r - an odds row is 1:N with N >= 1"
                                                % (b["id"], d["n"], k, v))
                        if v <= 50:
                            odds_under_50.append(v)
        self.assertGreaterEqual(len(odds_under_50), 10,
                                "premise: real 1:N rows at or under 50 exist (the old sentinel misread them)")
        anni = [d for b in self.bosses if b["id"] == "dclone" for d in b["dropTable"] if d["n"] == "Annihilus"][0]
        self.assertEqual({anni[k] for k in DIFFS}, {1}, "Diablo Clone always drops Annihilus (vanilla, labelled)")
        for bid, name in [e for e in EVENTS if e[1] != "Annihilus"]:
            row = [d for b in self.bosses if b["id"] == bid for d in b["dropTable"] if d["n"] == name][0]
            self.assertEqual([row[k] for k in ("norm", "normTz", "nm", "nmTz")], [None] * 4,
                             "%s drops on Normal or Nightmare in the data - keys are Hell only" % name)
            self.assertTrue(0 < row["hell"] < 0.2, "%s Hell holds %r" % (name, row["hell"]))
        dclone = [b for b in self.bosses if b["id"] == "dclone"][0]
        self.assertTrue(all("Annihilus 100%" in d["tc"] and "vanilla D2R" in d["tc"] for d in dclone["diffs"]),
                        "the Diablo Clone card does not label Annihilus 100% as the vanilla figure")
        summ = [b for b in self.bosses if b["id"] == "summoner"][0]
        self.assertEqual([d["tc"] for d in summ["diffs"][:4]], ["no Key of Hate (Hell only)"] * 4)

    def test_the_mf_curve_is_the_one_silospen_measures(self):
        """REG-2508 - every stored 1:N is silospen's at MF 300; moved to another MF it must land on silospen's figure."""
        self.assertEqual(_adjust(79, 699), SILOSPEN[("Nagelring", "Normal Andariel", 79)][699],
                         "premise: the game's curve reproduces silospen's 1:66")
        for (item, boss, base), at in SILOSPEN.items():
            for mf, want in at.items():
                got = self.o["curve"].get("%d@%d" % (base, mf))
                if got is None:
                    continue
                # the stored base is itself rounded, so a far MF may land one count off; the old cap-share line
                # was 6-35% off (Nagelring 1:70 at 699, 1:122 at 0)
                self.assertLessEqual(abs(got - want), max(1, round(want * 0.002)),
                                     "%s from %s at MF %d: the page says 1:%s, silospen 1:%d" % (item, boss, mf, got, want))
        self.assertEqual(self.o["eff699"], "184.14", "the dock's eff unique at MF 699 is not the game's 184%")

    def test_every_surface_states_the_same_curve(self):
        s = self.src
        self.assertIn('eff unique: <strong id="eff-mf">184.14%</strong>', s, "the dock's first paint says another MF")
        self.assertIn("<code>Effective MF = (Gear MF × Factor) / (Gear MF + Factor)</code>", s)
        stats = re.findall(r'<div class="stat-label">(\d+)% (?:MF|\(ref\)|\(you\)|\(max\))</div><div class="stat-value">'
                           r'([\d.]+)%</div><div class="stat-sub">effective unique</div>', s)
        self.assertEqual(len(stats), 4, "premise: the MF math section's four stats (%r)" % stats)
        for mf, shown in stats:
            want = int(mf) * 250.0 / (int(mf) + 250.0)
            self.assertEqual(shown, "%.1f" % want, "the MF math section says %s%% at MF %s, the curve %.1f%%" % (shown, mf, want))
        self.assertIn("effMF = MF × 250 / (MF + 250)", s, "the MF card no longer states the curve")
        self.assertNotIn("(Gear MF × 100)", s)

    def test_nagelring_keeps_its_odds_at_his_mf_and_at_a_full_game(self):
        o = self.o
        want699 = SILOSPEN[("Nagelring", "Normal Andariel", 79)][699]
        self.assertEqual(o["nag699"], want699, "Nagelring at MF 699 /players 1 is not silospen's 1:66")
        self.assertEqual(o["nag699fmt"], "1:66")
        self.assertIsNotNone(o["nag699hours"])
        self.assertIsNotNone(o["nag699runs"])
        # /players 8 (= 7, the game pairs them): the page's own factor, and silospen's figure for it (REG-2953)
        model = max(1, int(math.floor(_adjust(79, 1000) / _player_mult(self.player_f["andariel"]["norm"], 8) + 0.5)))
        self.assertEqual(o["nag1000"], model, "effChance did not apply the MF curve and the /players factor it states")
        self.assertEqual(model, _silospen_mf("Nagelring", 1000, 7), "Nagelring at MF 1000 /players 8 is not silospen's 1:35")
        self.assertLess(o["nag1000"], SILOSPEN[("Nagelring", "Normal Andariel", 79)][1000], "/players 8 did not move 1:N")
        self.assertEqual(o["nag1000fmt"], "1:%d" % model, "a 1:N at MF 1000 /players 8 printed as a percent")
        self.assertIsNotNone(o["nag1000hours"])
        self.assertEqual(o["nag1000runHours"], o["nag1000hours"])

    def test_a_small_odds_value_is_still_scaled_by_players(self):
        want = max(1, int(math.floor(_adjust(32, 1000) / _player_mult(self.player_f["mephisto"]["norm"], 8) + 0.5)))
        self.assertLess(want, _adjust(32, 1000), "premise: /players 8 moves this value")
        self.assertEqual(self.o["isen1000"], want, "an MF-adjusted 1:N at or under 50 skipped the /players scaling")
        self.assertEqual(self.o["isenRawFmt"], "1:32")
        self.assertIsNotNone(self.o["isenHours"])

    def test_an_event_drop_is_a_probability_never_timed(self):
        o = self.o
        self.assertEqual(o["anniFmt"], "100%")
        self.assertEqual(o["anniEff"], 1)
        self.assertIsNone(o["anniHours"])
        self.assertIsNone(o["anniRuns"])
        self.assertEqual(o["anniPerRun"], 1, "an event drop's per-run chance is p itself")
        self.assertEqual(o["anniRate"], 0, "an untimed event row adds a finds-per-hour rate")
        self.assertEqual(o["keyEff"], 0.0862, "MF or /players moved an event probability")
        self.assertEqual(o["keyAdj"], 0.0862)
        self.assertEqual(o["keyPerRun"], 0.0862)
        self.assertIsNone(o["keyHours"])
        self.assertIsNone(o["keyRunHours"])

    def test_a_key_prints_the_sourced_band(self):
        """REG-2503 - each key prints silospen's band for /players 1-8, labelled; never a single picked figure."""
        bands = {n: _band(ps) for n, ps in KEY_SILOSPEN.items()}
        self.assertEqual(bands, {"Key of Terror": "7.1-9.8%", "Key of Hate": "8.6-12.8%", "Key of Destruction": "7.9-11.4%"},
                         "premise: the measured bands")
        self.assertEqual(self.o["terrorFmt"], bands["Key of Terror"])
        self.assertEqual(self.o["keyFmt"], bands["Key of Hate"])
        self.assertEqual(self.o["destFmt"], bands["Key of Destruction"])
        cards = dict((n, r) for n, r in self.o["cards"])
        for n, band in bands.items():
            self.assertEqual(cards[n], "%s (Hell only · %s)" % (band, KEY_BAND_LABEL), "%s card: %r" % (n, cards[n]))
        for n, ps in KEY_SILOSPEN.items():
            row = [d for b in self.bosses for d in b["dropTable"] if d["n"] == n][0]
            self.assertEqual(row["hell"], round(ps[0], 4), "%s Hell holds %r, silospen /players 1 is %.4f" % (n, row["hell"], ps[0]))
        note = self.o["keyNote"]
        for n, band in bands.items():
            lo, hi = band[:-1].split("-")
            self.assertIn("%s %s%% to %s%%" % (n.split()[-1], lo, hi), note)
        self.assertNotIn("d2runewizard", note, "the key note quotes a second, different /players 1 figure again")
        self.assertNotRegex(self.src, r"~(?:8-9|9-13|10)% \(Hell only\)", "a key card prints a picked figure again")
        self.assertEqual(self.o["anniDrop"], "100%")
        self.assertEqual(self.o["oddsDrop"], "1:49")

    def test_render_detail_ranks_and_prints_the_good_mf_source(self):
        d699, d1000 = self.o["detail699"], self.o["detail1000"]
        model = max(1, int(math.floor(_adjust(79, 1000) / _player_mult(self.player_f["andariel"]["norm"], 8) + 0.5)))
        for html, odds in ((d699, "1:66"), (d1000, "1:%d" % model)):
            # the ranked row is the best cell, and the deep dive is built for it - both only when it ranks
            self.assertIn('<td class="diff-col best-cell ">%s</td>' % odds, html,
                          "the source fell out of its own ranking at " + odds)
            self.assertIn("\u00b7 %s chance \u00b7" % odds, html, "the deep dive is not built for the ranked source")
            self.assertNotRegex(html, r'<td class="diff-col[^"]*">\s*\d+(?:\.\d+)?%\s*</td>',
                                "a 1:N printed as a percent in the item ranking")
        key = self.o["detailKey"]
        self.assertIn(">8.6-12.8%<", key, "the key's row does not print its sourced band")
        self.assertNotIn("puv-deep-dive", key, "an event drop was timed as the fastest farm")

    def test_no_site_reads_a_unit_from_a_magnitude(self):
        s = self.src
        self.assertEqual(len(re.findall(r"<= ?EVENT_PCT_MAX|<= ?\(typeof EVENT_PCT_MAX", s)), 0,
                         "a site still reads the unit off the retired 50 line")
        self.assertNotIn("isPctC", s, "the aid card's own percent convention is back")
        for pat in (r"adjustedChance >= 100", r"adjustedChance < 100", r"s\.adj >= 100", r"v >= 100\)", r"val < 100\)"):
            self.assertIsNone(re.search(pat, s), "a magnitude threshold on an adjusted chance is back: " + pat)
        self.assertEqual(s.count("const isEventP = "), 1)


RED_PROOF = [
    {"why": "REG-2508 - the MF curve is the cap share again (MF x 100), so MF 699 prints Nagelring 1:70 against silospen 1:66",
     "file": "bible.html",
     "find": "const effMF = (gMF, factor) => (gMF*factor)/(gMF+factor);",
     "replace": "const effMF = (gMF, factor) => (gMF*100)/(gMF+factor);",
     "matches": 1},
    {"why": "REG-2508 - the dock's first paint says eff unique 73.66% again",
     "file": "bible.html",
     "find": "eff unique: <strong id=\"eff-mf\">184.14%</strong>",
     "replace": "eff unique: <strong id=\"eff-mf\">73.66%</strong>",
     "matches": 1},
    {"why": "REG-2508 - the MF math section states the cap-share formula again",
     "file": "bible.html",
     "find": "<code>Effective MF = (Gear MF × Factor) / (Gear MF + Factor)</code>",
     "replace": "<code>Effective MF = (Gear MF × 100) / (Gear MF + Factor)</code>",
     "matches": 1},
    {"why": "REG-2508 - the MF math section says 73.7% effective at MF 699 again",
     "file": "bible.html",
     "find": "<div class=\"stat-label\">699% (you)</div><div class=\"stat-value\">184.1%</div>",
     "replace": "<div class=\"stat-label\">699% (you)</div><div class=\"stat-value\">73.7%</div>",
     "matches": 1},
    {"why": "REG-2503 - the Key of Destruction card prints a single picked ~10% again",
     "file": "bible.html",
     "find": "rate: \"7.9-11.4% (Hell only · silospen RotW 3.0, /players 1-8)\",",
     "replace": "rate: \"~10% (Hell only)\",",
     "matches": 1},
    {"why": "REG-2503 - the key note quotes the d2runewizard ~8% beside silospen's 7.1% again",
     "file": "bible.html",
     "find": "important: \"Keys drop on Hell only, at any /players, and the chance rises with /players (it steps at /players 3, 5 and 7).",
     "replace": "important: \"Keys drop on Hell only, at any /players - the chance rises a little at higher /players (d2runewizard: the Countess ~8% at /players 1).",
     "matches": 1},
    {"why": "#63 - the unit rule is a magnitude sentinel again, so MF 1000 /players 8 prints Nagelring as 49%",
     "file": "bible.html",
     "find": "const isEventP = c => typeof c === 'number' && c > 0 && c <= 1;",
     "replace": "const isEventP = c => typeof c === 'number' && c > 0 && c <= EVENT_PCT_MAX;",
     "matches": 1},
    {"why": "#63 - effChance skips /players for a small adjusted 1:N again",
     "file": "bible.html",
     "find": "      if (a === null || isEventP(a)) return a;\n",
     "replace": "      if (a === null || a <= 50) return a;\n",
     "matches": 1},
    {"why": "#63 - renderDetail keeps only adjustedChance >= 100, so a good-MF source falls out of its own ranking",
     "file": "bible.html",
     "find": "  const valid = adjusted.filter(s => s.adjustedChance !== null && !isEventP(s.adjustedChance));",
     "replace": "  const valid = adjusted.filter(s => s.adjustedChance !== null && s.adjustedChance >= 100);",
     "matches": 1},
    {"why": "#63 - fmt prints any value at or under 50 as a percent again",
     "file": "bible.html",
     "find": "(isEventP(c) ? pctOf(c) : `1:${c.toLocaleString()}`)",
     "replace": "(c <= 50 ? `${c}%` : `1:${c.toLocaleString()}`)",
     "matches": 1},
    {"why": "#68 - the Key of Hate drops on Normal and Nightmare again",
     "file": "bible.html",
     "find": "\"norm\":null,\"normTz\":null,\"nm\":null,\"nmTz\":null,\"hell\":0.0862",
     "replace": "\"norm\":0.0862,\"normTz\":0.0862,\"nm\":0.0862,\"nmTz\":0.0862,\"hell\":0.0862",
     "matches": 1},
    {"why": "#62 - Annihilus is 12 on every difficulty again",
     "file": "bible.html",
     "find": "\"tier\":\"uber\",\"norm\":1,\"normTz\":1,\"nm\":1,\"nmTz\":1,\"hell\":1,\"hellTz\":1}",
     "replace": "\"tier\":\"uber\",\"norm\":12,\"normTz\":12,\"nm\":12,\"nmTz\":12,\"hell\":12,\"hellTz\":12}",
     "matches": 1},
    {"why": "#63 - hoursFor times an event drop",
     "file": "bible.html",
     "find": "  if (!chance || isEventP(chance) || !kph) return null;\n",
     "replace": "  if (!chance || !kph) return null;\n",
     "matches": 1},
    {"why": "#63 - an event drop's per-run chance is read as 1/p",
     "file": "bible.html",
     "find": "  if (isEventP(c)) return c;   // #63 — an event drop's per-run chance is p itself, never 1/p\n",
     "replace": "",
     "matches": 1},
    {"why": "#63 - an untimed event row adds a finds-per-hour rate to its run",
     "file": "bible.html",
     "find": "  if (isEventP(Number(chance))) return 0;   // #63 — an untimed event row adds no finds per hour to a run\n",
     "replace": "",
     "matches": 1},
    {"why": "#68 - a key prints a number of its own instead of its card's sourced band",
     "file": "bible.html",
     "find": "    const fmtDrop = (c, name) => (isEventP(c) && _eventFigure(name)) || fmt(c);",
     "replace": "    const fmtDrop = (c, name) => fmt(c);",
     "matches": 1},
    {"why": "#63 - MF scales an event probability",
     "file": "bible.html",
     "find": "  if (isEventP(base)) return base;\n",
     "replace": "",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
