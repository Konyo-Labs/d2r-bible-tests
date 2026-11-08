# -*- coding: utf-8 -*-
"""v3526 — ONE HUNT CLOCK: A RUN ROW, A PIECE CARD, A HERO AND THE CONSOLE READ THE SAME HOUR, FROM ONE PICK.

Konyo, 2026-09-30, on Cow King's Hooves — the one set piece he has left: "the time to hunt is not synced across here
and the sessions tab... here it says 84hrs. and in sets its like a million hours.. something is bugged i mentioned
this to you alraedy before. still rendering not correctly calculation wise. make sure its calliberated too."

MEASURED on the real page (headless Chrome, MF 699, 1 player, every set piece ticked but the Hooves), before the fix:
    Sets run row      "expected ~1 every 20030h of running"   kph / per-KILL odds: no kills-per-run
    Sets quick win    "1:140.2k ~40h to find"                 hoursFor with kills-per-run: right
    Sets hero         "best run: Normal TZ Hell Bovines 1:157.5k"  the RAW odds, and no time at all
    console Sessions  78.7h in Hell · "faster outside Hell ≈39.7h"   /api/evrank over the bridge: right
and every cow run was labelled "Hell Hell Bovines" / "Normal TZ Hell Bovines" (the boss row is named for its monster).
The run row was v2285's defect on the one line v2285 never reached; _pickSrc ranked every source on the same
per-kill rate, so 29 of 148 rows picked a different "best run" on the forge than the console hero already showed.

DRIVEN here, in node, over code CUT from bible.html between its own boundaries (never re-typed):
  · the engine block (EVENT_PCT_MAX .. pickFastest) · the clock spellings (_fmtHunt .. _kprChip) · _pickSrc
  · the Sets run grouping (renderForgeSets) and the Uniques run grouping (funiScan)
and JOINED to the console: control_app._ev_rank is run on the bridge-shaped row the page computes, and must print the
page's hour. The real page (bridge + forge + DOM) is driven by tests/v3526_one_hunt_clock.spec.ts on CI.

⚠ WHAT THIS LAW CANNOT SEE: pixels (looked at in headless Chrome at 1600 wide: hero, run row and quick win each read
"~40h", the Hell chip "~79h", the ~350/run chip), and the real _adjC (MF/players) — stood in by a fixed factor here so
"adjusted, not raw" stays observable; the spec runs the real one. The per-location run rates (kph) and kills-per-run
are hand-set estimates this law does not calibrate; the cards print them (~350/run, "assumes 7 runs/h").
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fixture_tmp as _fx_tmp  # noqa: E402  #171 — this run's scratch dirs leave with it
_fx_tmp.contain()
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

NODE = shutil.which("node")

_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const cut = (a, b, incl) => {
  const i = src.indexOf(a); if (i < 0) throw new Error('CUT START MISSING: ' + a.slice(0, 70));
  const j = src.indexOf(b, i); if (j < 0) throw new Error('CUT END MISSING: ' + b.slice(0, 70));
  return src.slice(i, incl ? j + b.length : j);
};
const ENGINE = cut('const EVENT_PCT_MAX = 50;', 'const fmtHours = h => {');
const CLOCK  = cut('  function _fmtHunt(h){', '  window._kprChip = _kprChip;', true);
const PICK   = cut('  function _pickSrc(sources, name){', '  window._pickSrc = _pickSrc;', true);
const SETS   = cut("    var NO_RUN_KEY = 'No verified farm source yet';", "g.hours=g.noRun?null:runHoursFor(g.rows); });", true);
const UNI    = cut('    missing.forEach(function(x){\n      var b=_bestSrc(x);', '    runs.forEach(function(r){ r.hours = runHoursFor(r.rows); });', true);

const SCEN = function(){
  const out = {};
  const row = (boss, bossId, chance, kph, diffKey) => ({ boss, bossId, chance, kph, diffKey });
  // the Hooves' real rows (raw per-kill odds, bible.html ITEM_REGISTRY), cow runs kill ~350 per run
  const HOOVES = [row('Normal Cow Level','cows',167545,7,'norm'), row('Normal TZ Cow Level','cows',157547,7,'normTz'),
                  row('NM Cow Level','cows',212519,7,'nm'), row('NM TZ Cow Level','cows',206087,7,'nmTz'),
                  row('Hell Cow Level','cows',267481,6,'hell'), row('Hell TZ Cow Level','cows',267575,6,'hellTz')];
  const NAME = "Cow King's Hooves";
  // 1 — the pick is the shortest hour, on the ADJUSTED odds, and carries that hour and the per-hour rate
  const p = _pickSrc(HOOVES, NAME);
  const adj = _adjC(HOOVES[1], NAME);
  out.pick = { boss: p.s.boss, chance: p.chance, hours: p.hours, rate: p.rate,
               wantHours: hoursFor(adj, 0.5, 7, killsPerRun('cows')), wantRate: findRate(adj, 'cows', 7),
               minOther: Math.min.apply(null, HOOVES.map(s => hoursFor(_adjC(s, NAME), 0.5, s.kph, killsPerRun(s.bossId)))) };
  // 2 — a boss whose PER-KILL rate is higher but whose HOUR is longer must lose to the area run
  const MEPH = row('Hell Mephisto','mephisto',9382,80,'hell'), COWS = row('Hell Cow Level','cows',200000,6,'hell');
  const pk = _pickSrc([MEPH, COWS], 'X');
  out.area = { boss: pk.s.boss, perKillLeader: ((MEPH.kph / _adjC(MEPH)) > (COWS.kph / _adjC(COWS))) ? MEPH.boss : COWS.boss,
               hMeph: hoursFor(_adjC(MEPH), 0.5, 80, 1), hCows: hoursFor(_adjC(COWS), 0.5, 6, 350) };
  // 3 — a tie in hours goes to the higher finds-per-hour rate, whatever order the rows arrive in
  const A = row('Hell Cow Level','cows',267481,6,'hell'), B = row('Hell TZ Cow Level','cows',267575,6,'hellTz');
  const tAB = pickFastest([A, B], s => _adjC(s)), tBA = pickFastest([B, A], s => _adjC(s));
  out.tie = { sameHour: hoursFor(_adjC(A), 0.5, 6, 350) === hoursFor(_adjC(B), 0.5, 6, 350), ab: tAB.s.boss, ba: tBA.s.boss };
  // 4 — runHoursFor: one row IS hoursFor; more drops is sooner; mixed kph / an event percentage / nothing -> null
  const one = (c, id, k) => ({ single: runHoursFor([{ chance: c, bossId: id, kph: k }]), hoursFor: hoursFor(c, 0.5, k, killsPerRun(id)) });
  out.identity = [one(140217, 'cows', 7), one(238058, 'cows', 6), one(8350, 'mephisto', 80), one(79, 'andariel', 90), one(1302, 'pit', 50)];
  const r1 = { chance: 140217, bossId: 'cows', kph: 7 }, r2 = { chance: 90000, bossId: 'cows', kph: 7 };
  out.multi = { both: runHoursFor([r1, r2]), a: runHoursFor([r1]), b: runHoursFor([r2]),
                mixedKph: runHoursFor([r1, { chance: 90000, bossId: 'cows', kph: 6 }]),
                eventPct: runHoursFor([r1, { chance: 12, bossId: 'dclone', kph: 3 }]), empty: runHoursFor([]) };
  // 5 — the SETS run row: one missing piece at the cow run reads exactly its card's hour, with kills-per-run in ev
  const setsG = (function(missingP){ var bySrc = {};
    eval(SETS_SRC);
    return bySrc; })([{ name: "Cow King's Hooves (heavy boots)", set: "Cow King's Leathers (set)", left: 1, src: HOOVES[1] }]);
  const g = setsG['Normal TZ Cow Level'];
  out.setsRun = g ? { hours: g.hours, ev: g.ev, clock: _runClock(g), card: _ttf(adj, 7, killsPerRun('cows')),
                      wantEv: findRate(adj, 'cows', 7), perKillEv: 7 / adj } : null;
  const setsTwo = (function(missingP){ var bySrc = {}; eval(SETS_SRC); return bySrc; })([
    { name: 'P1', set: 'S', left: 2, src: HOOVES[1] }, { name: 'P2', set: 'S', left: 2, src: row('Normal TZ Cow Level','cows',90000,7,'normTz') }]);
  out.setsTwo = { clock: _runClock(setsTwo['Normal TZ Cow Level']), hours: setsTwo['Normal TZ Cow Level'].hours };
  // 6 — the UNIQUES run grouping: each run's clock is its drops' own hour
  const _bestSrc = it => _pickSrc(it && it.sources, it && it.n);
  const uniRuns = (function(missing){ var bySrc = {}; eval(UNI_SRC); return runs; })([
    { n: 'Hooves-like', sources: HOOVES }, { n: 'Meph-only', sources: [MEPH] }]);
  out.uni = uniRuns.map(r => ({ boss: r.boss, hours: r.hours, n: r.items.length, bs: r.items[0]._bs.hours, clock: _runClock(r) }));
  // 7 — the kills-per-run chip names the estimate on an AREA run and nothing on a boss
  out.chip = { cows: _kprChip('cows'), meph: _kprChip('mephisto') };
  // 8 — the ONE row the console ranks: the bridge ships perRunChance(adj) with the run rate
  out.bridge = { dropChance: perRunChance(adj, 'cows'), killsPerHr: srcKph(HOOVES[1]), pageHours: hoursFor(adj, 0.5, 7, 350),
                 hellDrop: perRunChance(_adjC(HOOVES[4], NAME), 'cows'), hellKph: 6, pageHell: hoursFor(_adjC(HOOVES[4], NAME), 0.5, 6, 350) };
  return out;
};

const ctx = {
  // v3884 (REG-3435) - a terror-zone row competes only while the live rotation names its zone. This law's subject is ONE
  // CLOCK, not the rotation, so the Cow Level is read as terrorized now and its TZ rows compete exactly as before; the
  // rotation rule itself is test_a_terror_zone_run_ranks_only_in_its_slot.
  window: { _tzPeek: () => ({ current: 'Secret Cow Level', ts: Date.now() }) },
  TZ_HUNT: [{ id: 'cows', m: ['cow level', 'moo moo farm'] }], _tzTurnBoundary: (t) => t + 3600000,
  console, Math, JSON, isFinite, Number, String, Object, Array, Infinity, Date,
  esc: (s) => String(s),
  // a fixed MF factor stands in for effChance, so an ADJUSTED figure is distinguishable from the raw row
  _adjC: (s) => (s && s.chance != null) ? Math.round(s.chance * 0.89) : null,
  _diffRank: (k) => /^hell/.test(String(k)) ? 2 : (/^nm/.test(String(k)) ? 1 : 0),
  _diffLabel: (d) => ['Normal', 'NM', 'Hell'][d] || '',
  SETS_SRC: SETS, UNI_SRC: UNI,
};
vm.createContext(ctx);
const script = ENGINE + '\n' + CLOCK + '\n' + PICK + '\n'
  + 'var _ttf = function(chance, kph, kpr){ var h = hoursFor(chance, 0.5, kph, kpr); return _fmtHunt(h); };\n'
  + '(' + SCEN.toString() + ')()';
process.stdout.write(JSON.stringify(vm.runInContext(script, ctx)));
"""


def _drive(src=None):
    path = src or os.path.join(ROOT, "bible.html")
    d = tempfile.mkdtemp(prefix="hunt_clock_")
    try:
        drv = os.path.join(d, "driver.js")
        with io.open(drv, "w", encoding="utf-8") as fh:
            fh.write(_DRIVER)
        r = subprocess.run([NODE, drv, path], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("driver failed: " + (r.stderr or r.stdout)[-1500:])
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


@unittest.skipUnless(NODE, "node is required to drive the page's own code")
class TheHuntHasOneClock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = _drive()

    def test_the_pick_is_the_shortest_hour_on_the_adjusted_odds(self):
        p = self.o["pick"]
        self.assertEqual(p["boss"], "Normal TZ Cow Level")
        self.assertEqual(p["chance"], round(157547 * 0.89), "the pick prints the ADJUSTED odds, never the raw row")
        self.assertEqual(p["hours"], p["wantHours"], "the pick carries the very hour its card prints")
        self.assertEqual(p["hours"], p["minOther"], "and no other source of the piece is quicker")
        self.assertAlmostEqual(p["rate"], p["wantRate"], places=12)

    def test_an_area_run_is_priced_per_run_not_per_kill(self):
        a = self.o["area"]
        # the defect's own shape: on per-KILL rate the boss leads...
        self.assertEqual(a["perKillLeader"], "Hell Mephisto")
        self.assertLess(a["hCows"], a["hMeph"], "...while the cow run is the shorter hour")
        # ...and the pick must be the shorter hour — the one the console hero already named
        self.assertEqual(a["boss"], "Hell Cow Level")

    def test_a_tie_in_hours_names_the_same_run_whatever_the_row_order(self):
        t = self.o["tie"]
        self.assertTrue(t["sameHour"], "the fixture must really tie, or this case proves nothing")
        self.assertEqual(t["ab"], "Hell Cow Level")
        self.assertEqual(t["ba"], "Hell Cow Level", "first-row-wins named a different run on the console for one hour")

    def test_a_run_with_one_drop_reads_exactly_hoursFor(self):
        for i, c in enumerate(self.o["identity"]):
            self.assertIsNotNone(c["single"], "case %d" % i)
            self.assertEqual(c["single"], c["hoursFor"], "case %d: the run clock and the card clock must be one" % i)

    def test_more_drops_is_sooner_and_unknown_stays_unknown(self):
        m = self.o["multi"]
        self.assertLess(m["both"], min(m["a"], m["b"]))
        self.assertGreater(m["both"], 0)
        self.assertIsNone(m["mixedKph"], "two run rates in one run is not a run — no averaged hour")
        self.assertIsNone(m["eventPct"], "an event percentage is not timed by hoursFor — not here either")
        self.assertIsNone(m["empty"])

    def test_the_sets_run_row_reads_its_pieces_card_hour(self):
        g = self.o["setsRun"]
        self.assertIsNotNone(g, "the Sets grouping must key the run by its label")
        self.assertIn("~" + g["card"] + "</b> to find it", g["clock"], "run row and quick-win card print one hour")
        self.assertEqual(g["card"], "40h")
        self.assertAlmostEqual(g["ev"], g["wantEv"], places=12)
        self.assertGreater(g["ev"] / g["perKillEv"], 300, "ev must count the ~350 cows a run kills")
        self.assertIn("title=\"assumes 7 runs/h", g["clock"], "the hour names what it assumes")
        self.assertIn("~350 kills per run", g["clock"])
        two = self.o["setsTwo"]
        self.assertIn("to find one", two["clock"])

    def test_the_uniques_runs_carry_their_drops_hour(self):
        runs = {r["boss"]: r for r in self.o["uni"]}
        self.assertIn("Normal TZ Cow Level", runs)
        self.assertIn("Hell Mephisto", runs)
        for r in runs.values():
            self.assertEqual(r["n"], 1)
            self.assertEqual(r["hours"], r["bs"], r["boss"] + ": the run's clock is its one drop's own hour")
            self.assertIn("to find it", r["clock"])

    def test_the_area_estimate_is_named_on_the_card(self):
        self.assertIn("~350/run", self.o["chip"]["cows"])
        self.assertEqual(self.o["chip"]["meph"], "")

    def test_the_console_ranks_the_page_hour(self):
        import control_app
        b = self.o["bridge"]
        r = control_app._ev_rank([{"name": "Cow King's Hooves", "source": "Normal TZ Cow Level",
                                   "dropChance": b["dropChance"], "killsPerHr": b["killsPerHr"],
                                   "hellSource": "Hell Cow Level", "hellDropChance": b["hellDrop"],
                                   "hellKillsPerHr": b["hellKph"]}])
        row = r["ranked"][0]
        self.assertEqual(row["expectedHours"], round(b["pageHours"], 2), "/api/evrank and the page must print one hour")
        self.assertEqual(row["hellExpectedHours"], round(b["pageHell"], 2))

    def test_no_run_is_named_twice_for_its_difficulty(self):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            src = fh.read()
        i = src.index("\nconst ITEM_REGISTRY = {};")
        block = src[i:src.index("\n});", i)]   # the BOSSES.forEach that builds every source closes at column 0
        self.assertIn("item.sources.push", block, "the cut must hold the source builder, or this case proves nothing")
        self.assertNotIn("${label} ${boss.name}", block,
                         "a source label built from the monster's name reads 'Hell Hell Bovines'")
        self.assertIn("{boss:`${label} ${runName}`", block)
        self.assertIn("({ cows: 'Cow Level' })[boss.id] || boss.name", block)


RED_PROOF = [
    {
        "why": "v3526 - the forge picker ranks on kph / per-KILL odds again, so a cow run loses to a slower boss",
        "file": "bible.html",
        "find": "    var p=pickFastest(sources, function(s){ return _adjC(s, name); });\n",
        "replace": "    var p=null; (sources||[]).forEach(function(s){ if(!s||s.blocked||s.chance==null) return; var c=_adjC(s,name), r=(s.kph||30)/c; if(!p||r>p.rate) p={s:s,chance:c,rate:r,hours:hoursFor(c,0.5,s.kph,killsPerRun(s.bossId))}; });\n",
        "matches": 1,
    },
    {
        "why": "v3526 - a tie in hours goes to the first row, so two surfaces can name different runs for one hour",
        "file": "bible.html",
        "find": "    if (h < bestH || (h === bestH && r > bestR)) { best = s; bestH = h; bestR = r; bestC = c; }\n",
        "replace": "    if (h < bestH) { best = s; bestH = h; bestR = r; bestC = c; }\n",
        "matches": 1,
    },
    {
        "why": "v3526 - the Sets run row sums kph / per-KILL odds again ('~1 every 20030h' under a 40h piece)",
        "file": "bible.html",
        "find": "        g.ev+=findRate(_ac, mp.src.bossId, srcKph(mp.src));\n",
        "replace": "        g.ev+=srcKph(mp.src)/_ac;\n",
        "matches": 1,
    },
    {
        "why": "v3526 - a run's clock is an independent-sum mean again instead of hoursFor's whole-run arithmetic",
        "file": "bible.html",
        "find": "  return Math.ceil(Math.log(1 - conf) / logMiss) / kph;\n",
        "replace": "  return Math.log(1 - conf) / logMiss / kph;\n",
        "matches": 1,
    },
    {
        "why": "v3526 - the run row loses the assumptions its hour rests on",
        "file": "bible.html",
        "find": "    return ' · <b' + (why ? ' title=\"assumes ' + why + '\"' : '') + '>~' + t + '</b> to find ' + ((r.items && r.items.length === 1) ? 'it' : 'one');\n",
        "replace": "    return ' · <b>~' + t + '</b> to find ' + ((r.items && r.items.length === 1) ? 'it' : 'one');\n",
        "matches": 1,
    },
    {
        "why": "v3526 - the cow run is named for its monster again ('Hell Hell Bovines')",
        "file": "bible.html",
        "find": "        item.sources.push({boss:`${label} ${runName}`,chance,bossId:boss.id,verified:isVer,kph:effKph,diffKey:k});\n",
        "replace": "        item.sources.push({boss:`${label} ${boss.name}`,chance,bossId:boss.id,verified:isVer,kph:effKph,diffKey:k});\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
