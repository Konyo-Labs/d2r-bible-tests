# -*- coding: utf-8 -*-
"""v3884 (REG-3435) - A TERROR-ZONE RUN RANKS ONLY WHILE ITS ZONE IS TERRORIZED.

His words 2026-11-08 11:18-11:21, with silospen's dropcalc beside the console (RotW, MF 700, Terror Zone OFF): "why does the
console read not correctly for the heavens light?", "Hell mode and not nightmare.. its a lvl 71 item", "based on the odds
for heavens light these are the top list". The console's Best runs and Quick wins named NM TZ Mephisto, NM TZ Diablo and
NM TZ Baal first (1:1.6k each at his MF). MEASURED 11-08 against silospen's own API (MF 0, /players 1):
  Terror Zone ON (NM, desecratedLevel 76 or 99):  Mephisto, Diablo, Baal 1:4,292 each · Andariel 1:6,411
  Terror Zone OFF:  Hell Andariel 1:7,615 · Hell Mephisto 1:8,906 · Hell Diablo 1:9,155 · Hell Baal 1:9,246 · NM Baal 1:19,294
So the TZ figures ARE silospen's - the defect was ranking them as runs he can do any time. A zone is terrorized for its own
slot. Now the ONE picker (pickFastest - Best runs, every card, the console bridge), Quick wins (_qwPlaces) and the item
landing (d2rOpenItem) let a TZ row compete only while the live rotation (window._tzPeek - the TZ tracker's /api/tz reading)
was read in THIS slot (_tzTurnBoundary) and names the row's zone (TZ_HUNT's own words). No reading, an old one, a stale one,
or a zone with no words -> the always-runnable rows rank, which is silospen's list with Terror Zone off.

Drives the page's own code in node (cut from bible.html): TZ_HUNT, _tzTurnBoundary, the engine with tzRowLive and
pickFastest, _pickSrc and _qwPlaces, on Heaven's Light's measured rows. RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")

_DRIVER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[2], 'utf8');
const cut = (a, b, incl) => {
  const i = src.indexOf(a); if (i < 0) throw new Error('CUT START MISSING: ' + a.slice(0, 70));
  if (src.indexOf(a, i + 1) >= 0) throw new Error('CUT START NOT UNIQUE: ' + a.slice(0, 70));
  const j = src.indexOf(b, i); if (j < 0) throw new Error('CUT END MISSING: ' + b.slice(0, 70));
  return src.slice(i, incl ? j + b.length : j);
};
const HUNT   = cut('const TZ_HUNT = [', '\n];\n', true);
const TURN   = cut('function _tzTurnBoundary(now){', '\n}\n', true);
const ENGINE = cut('const EVENT_PCT_MAX = 50;', 'const fmtHours = h => {');
const PICK   = cut('  function _pickSrc(sources, name){', '  window._pickSrc = _pickSrc;', true);
const QW     = cut('  var _QW_DIFF = {', '  window._qwPlaces = _qwPlaces;', true);
const T0 = Date.UTC(2026, 10, 8, 9, 10, 0);    // 11:10 IST - mid-slot
const HL = [  // Heaven's Light, silospen MF 0 /players 1 (raw per-kill odds), one kph so only the odds decide
  ['NM TZ Mephisto', 'mephisto', 4292, 'nmTz'], ['NM TZ Diablo', 'diablo', 4292, 'nmTz'], ['NM TZ Baal', 'baal', 4292, 'nmTz'],
  ['NM TZ Andariel', 'andariel', 6411, 'nmTz'], ['Hell Andariel', 'andariel', 7615, 'hell'], ['Hell Mephisto', 'mephisto', 8906, 'hell'],
  ['Hell Diablo', 'diablo', 9155, 'hell'], ['Hell Baal', 'baal', 9246, 'hell'], ['NM Baal', 'baal', 19294, 'nm'],
  ['Hell TZ Mephisto', 'mephisto', 9573, 'hellTz'], ['NM TZ Nihlathak', 'nihl', 31959, 'nmTz']
].map(r => ({ boss: r[0], bossId: r[1], chance: r[2], diffKey: r[3], kph: 20 }));
const ctx = { console, Math, JSON, isFinite, Number, String, Object, Array, Infinity, Date, window: {},
              _adjC: (s) => (s && s.chance != null) ? s.chance : null,
              _diffRank: (k) => /^hell/.test(String(k)) ? 2 : (/^nm/.test(String(k)) ? 1 : 0) };
vm.createContext(ctx);
const read = (cur, ts, stale) => { ctx.window._tzPeek = cur == null ? undefined : () => ({ current: cur, ts: ts, stale: stale }); };
const run = 'var _realNow = Date.now; ' + HUNT + '\n' + TURN + '\n' + ENGINE + '\n' + PICK + '\n' + QW + '\n'
  + 'globalThis._tzTurnBoundary = _tzTurnBoundary; globalThis.TZ_HUNT = TZ_HUNT; globalThis.tzRowLive = tzRowLive;'
  + 'globalThis._pickSrc = _pickSrc; globalThis._qwPlaces = _qwPlaces;';
vm.runInContext(run, ctx);
const at = (cur, ts, stale) => {
  read(cur, ts, stale);
  ctx.Date.now = () => T0;
  const p = ctx._pickSrc(HL, "Heaven's Light");
  const q = ctx._qwPlaces({ n: "Heaven's Light", sources: HL }).map(x => x.label);
  const live = HL.filter(s => /Tz$/.test(s.diffKey) && ctx.tzRowLive(s, T0)).map(s => s.boss);   // the TZ rows it wakes
  return { pick: p && p.s.boss, qw: q.slice(0, 5), live: live };
};
const out = {
  none: at(null),
  durance: at('Durance of Hate', T0 - 60000),
  oldSlot: at('Durance of Hate', T0 - 3 * 3600 * 1000),
  stale: at('Durance of Hate', T0 - 60000, true),
  noTs: at('Durance of Hate', 0),
  elsewhere: at('Lost City, Valley of Snakes, and Claw Viper Temple', T0 - 60000),
  halls: at('Halls of Pain', T0 - 60000),
};
console.log(JSON.stringify(out));
"""

TZ_OFF = ["Hell Andariel", "Hell Mephisto", "Hell Diablo", "Hell Baal", "NM Baal"]


def _code():
    with io.open(BIBLE, encoding="utf-8") as fh:
        src = fh.read()
    src = re.sub(r"/\*.{0,4000}?\*/", "", src, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", r"\1", ln) for ln in src.split("\n"))


@unittest.skipIf(NODE is None, "node is not on this machine - this law RUNS the page's picker, UNMEASURED here")
class ATerrorZoneRunRanksOnlyInItsSlot(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        r = subprocess.run([NODE, "-", BIBLE], input=_DRIVER, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError("node could not run the page's picker - UNKNOWN, not passing: %s" % r.stderr[-600:])
        cls.o = json.loads(r.stdout.strip().splitlines()[-1])

    def test_with_no_reading_the_list_is_silospens_with_terror_zone_off(self):
        """* THE POINT - Heaven's Light: Hell Andariel, Hell Mephisto, Hell Diablo, Hell Baal, NM Baal - his dropcalc list"""
        o = self.o["none"]
        self.assertEqual(o["pick"], "Hell Andariel", "the best run is a terror-zone run nobody said is terrorized: %r" % o)
        self.assertEqual(o["qw"], TZ_OFF, "Quick wins is not silospen's Terror-Zone-off order")
        self.assertEqual(o["live"], [], "a TZ row read as terrorized with no rotation reading")

    def test_while_its_zone_is_terrorized_the_tz_run_ranks(self):
        o = self.o["durance"]
        self.assertEqual(o["pick"], "NM TZ Mephisto", "Durance of Hate is terrorized and its TZ run did not rank: %r" % o)
        self.assertEqual(o["live"], ["NM TZ Mephisto", "Hell TZ Mephisto"],
                         "only Durance of Hate's TZ rows are live - NM TZ Diablo and NM TZ Baal are not in that zone")
        self.assertEqual(o["qw"][1:5], TZ_OFF[:4])

    def test_an_old_stale_or_untimed_reading_is_no_reading(self):
        for k in ("oldSlot", "stale", "noTs"):
            self.assertEqual(self.o[k]["live"], [], "%s: a reading that cannot speak for this slot made a TZ row live" % k)
            self.assertEqual(self.o[k]["qw"], TZ_OFF, k)

    def test_another_zone_terrorized_leaves_these_rows_waiting(self):
        self.assertEqual(self.o["elsewhere"]["live"], [])
        self.assertEqual(self.o["elsewhere"]["pick"], "Hell Andariel")

    def test_nihlathaks_halls_ride_the_pindle_nihlathak_words(self):
        self.assertEqual(self.o["halls"]["live"], ["NM TZ Nihlathak"], "Halls of Pain terrorized did not wake Nihlathak's TZ row")

    def test_the_item_landing_asks_the_same_rule(self):
        code = _code()
        self.assertIn("if (typeof tzRowLive === 'function' && !tzRowLive(s)) return;", code,
                      "d2rOpenItem picks its best source with TZ rows the picker refuses - the landing and the cards disagree")


RED_PROOF = [
    {"why": "v3884 - the one picker ranks a TZ run whatever the rotation says (Heaven's Light: NM TZ Mephisto first again)",
     "file": "bible.html",
     "find": "    if (!tzRowLive(s)) continue;                                   // v3884 (REG-3435) - a TZ run outside its zone's slot\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "v3884 - Quick wins ranks a TZ run whatever the rotation says",
     "file": "bible.html",
     "find": "        if (!tzRowLive(s)) return;                       /* v3884 (REG-3435) - a TZ run ranks only in its zone's slot */\n",
     "replace": "", "matches": 1, "needs": "node"},
    {"why": "v3884 - a reading from an older slot still makes a TZ row live (the zone has rotated)",
     "file": "bible.html",
     "find": "    if (typeof _tzTurnBoundary !== 'function' || now >= _tzTurnBoundary(Number(d.ts))) return false;",
     "replace": "    if (typeof _tzTurnBoundary !== 'function') return false;",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - any reading makes every TZ row live, whatever zone it names",
     "file": "bible.html",
     "find": "    return !!(h && Array.isArray(h.m) && h.m.some(w => cur.indexOf(w) >= 0));",
     "replace": "    return true;",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - a stale reading counts",
     "file": "bible.html",
     "find": "    if (!d || d.stale || typeof d.current !== 'string'",
     "replace": "    if (!d || typeof d.current !== 'string'",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - the item landing picks a TZ row the picker refuses",
     "file": "bible.html",
     "find": "        if (typeof tzRowLive === 'function' && !tzRowLive(s)) return;   // v3884 (REG-3435) - the picker's own TZ rule\n",
     "replace": "", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
