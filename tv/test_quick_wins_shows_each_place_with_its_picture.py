# -*- coding: utf-8 -*-
"""#85 (his ask 2026-11-06, a screenshot of the Gull and Bane Ash cards) - QUICK WINS SHOWS EACH PLACE AS ONE ROW OF A GRID,
WITH ITS PICTURE AND A SUBTITLE UNDER EVERY NUMBER.

His words: "i want this designed better with hd art image for each area and the rows symmetric and organized and each
rendering in an organized grid with subtitles for each row ... and with the images for each boss/level that we are
farming". The 1st place was a sentence and the 2nd-4th loose chips; nothing lined up and no number said what it was.

The law drives the page's OWN code in node (cut from bible.html: TZ_INFO, tzKey/tzArtFor, BOSSES, BOSS_PORTRAIT and the
grid's functions) - never a Python copy of the zone rule:
  1. every place Quick wins can rank (QW_TARGETS and every boss in QW_PLACES) gets its zone's level art, and the file is
     in art/; Radament's "Sewers Level 3" is Lut Gholein's (act 2), never Kurast's; "Durance of Hate L3" resolves too;
  2. every monster picture the grid names is a file in art/ (a boss's HD portrait, a super-unique's own sprite);
  3. a ranked row is one tile + the place + four numbers, each number over its own subtitle, and the odds column says
     one unit for every row ("odds a run" - the Grok CLI's look found a kill compared with a run);
  4. the per-kill places are their own section, under their own heading, never mixed into the ranked rows.
RED_PROOF below.
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
ROOT = os.path.dirname(HERE)
NODE = shutil.which("node") or shutil.which("nodejs")


def _read():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end, keep_end=True):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    j = src.index(end, i + len(start))
    return src[i:j + (len(end) if keep_end else 0)]


def _table(src, name):
    m = re.search(r"\nconst %s = (\{.*?\});\n" % re.escape(name), src)
    if not m:
        raise AssertionError("the page carries no %s table" % name)
    return json.loads(m.group(1))


HARNESS = r"""
var window = {};
function esc(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
function _fmtHunt(h){ return (h < 10 ? (Math.round(h * 10) / 10) : Math.round(h)) + 'h'; }
function _qwRunsTxt(n){ return '~' + n + ' runs'; }
var KPR = { pit: 110 };
function perRunChance(c, id){ var n = KPR[id] || 1; return 1 - Math.pow(1 - 1 / c, n); }
function _artV(u){ return u; }
%(code)s
window.BOSS_PORTRAIT = BOSS_PORTRAIT;
var CFG = %(cfg)s, out = { zones: {}, tiles: {}, bossZones: {} };
Object.keys(CFG.targets).forEach(function(id){
  var T = CFG.targets[id];
  out.tiles[id] = _qwTile(id, T.a, T.n);
  out.zones[id] = _qwZoneArt(T.a);
});
CFG.bossIds.forEach(function(id){ var a = _qwAreaOf(id, ''); out.bossZones[id] = [a, _qwZoneArt(a), _qwTile(id, a, id)]; });
out.sewers = _qwZoneArt('Sewers Level 3');
out.durance = _qwZoneArt('Durance of Hate L3');
var places = [
  { label: 'Normal Coldcrow', area: 'Cave Level 1', s: { bossId: 'su_coldcrow' }, chance: 307, runs: 213, hours: 2.5, kph: 84, kpr: 1, est: true },
  { label: 'Normal Andariel', area: '', s: { bossId: 'andariel' }, chance: 741, runs: 514, hours: 4.8, kph: 108, kpr: 1, est: false },
  { label: 'Normal The Pit', area: '', s: { bossId: 'pit' }, chance: 87700, runs: 553, hours: 10, kph: 54, kpr: 110, est: false },
  { label: 'Normal Pitspawn Fouldog', area: 'Jail Level 2', s: { bossId: 'su_pitspawnfouldog' }, chance: 1000, runs: 699, hours: 9.7, kph: 72, kpr: 1, est: true }
];
var also = [ { id: 'su_thecowking', who: 'Normal The Cow King', area: 'The Secret Cow Level', kind: 'once', chance: 312 },
             { who: 'Normal The Banished', area: 'Catacombs Level 3', kind: 'unique', chance: 603 } ];
out.grid = _qwGridHtml(places, also);
out.gridNoAlso = _qwGridHtml(places, []);
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to drive the page's own grid code - UNMEASURED here, not a pass")
class QuickWinsShowsEachPlaceWithItsPicture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        src = _read()
        cls.targets = _table(src, "QW_TARGETS")
        places = _table(src, "QW_PLACES")
        bl = next(ln for ln in src.split("\n") if ln.startswith("const BOSSES = "))
        boss_ids = set(b["id"] for b in json.loads(bl[len("const BOSSES = "):][:bl[len("const BOSSES = "):].rindex("];") + 1]))
        cls.boss_ids = sorted(set(r[0] for p in places.values() for r in p.get("f") or [] if r[0] in boss_ids))
        tz = _cut(src, "  var TZ_INFO = {", "};\n")
        key = _cut(src, "  function tzKey(name){", "\n  }\n")
        art = _cut(src, "  function tzArtFor(name){", "\n")
        portrait = _cut(src, "  var BOSS_PORTRAIT = {", "\n  };\n")
        grid = _cut(src, "  var _QW_SU_ART = ", "  window._qwGridHtml = _qwGridHtml;")
        odds = _cut(src, "  function fmtOdds(c){", "\n")                      # the page's own 1:N formatter
        code = "\n".join([tz, key, art, bl.replace("const BOSSES", "var BOSSES", 1), portrait, odds, grid])
        js = HARNESS % {"code": code, "cfg": json.dumps({"targets": cls.targets, "bossIds": cls.boss_ids})}
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise AssertionError("the page's grid code would not run in node:\n%s" % r.stderr[-1500:])
        cls.o = json.loads(r.stdout)

    def _art_exists(self, url):
        return bool(url) and os.path.isfile(os.path.join(ROOT, url.split("?")[0]))

    def test_every_place_it_can_rank_wears_its_zones_art(self):
        missing = [(i, self.targets[i]["a"], self.o["zones"][i]) for i in self.targets if not self._art_exists(self.o["zones"][i])]
        self.assertEqual(missing, [], "a Quick wins place has no zone art on disk: %r" % missing)
        bad = [(i, a, z) for i, (a, z, _t) in self.o["bossZones"].items() if not self._art_exists(z)]
        self.assertEqual(bad, [], "a boss Quick wins ranks has no zone art on disk: %r" % bad)
        self.assertEqual(self.o["sewers"], "art/tz_act2-sewer.jpg", "Radament's sewers are Lut Gholein's (act 2)")
        self.assertTrue(self._art_exists(self.o["durance"]), "'Durance of Hate L3' found no zone art")

    def test_every_monster_picture_it_names_is_on_disk(self):
        named = []
        for tile in list(self.o["tiles"].values()) + [t for (_a, _z, t) in self.o["bossZones"].values()]:
            named += re.findall(r'<img class="qw-mon[^"]*" src="([^"]+)"', tile)
        self.assertTrue(named, "no tile carries a monster picture - the grid lost its art")
        gone = sorted(set(u for u in named if not self._art_exists(u)))
        self.assertEqual(gone, [], "the grid names pictures that are not in art/: %r" % gone)
        self.assertIn("art/Coldcrow.gif", named)
        self.assertIn("art/Andariel_graphic.png", named)

    def test_a_ranked_row_is_a_tile_a_place_and_four_captioned_numbers(self):
        g = self.o["gridNoAlso"]
        rows = re.findall(r'<div class="qw-row(?: qw-best)?">(.*?)</div>', g)
        self.assertEqual(len(rows), 4, "four places did not make four rows: %s" % g[:300])
        self.assertIn('<div class="qw-row qw-best">', g, "the best place is not marked")
        for row in rows:
            self.assertEqual(row.count('class="qw-tile'), 1, row[:200])
            stats = re.findall(r'<span class="qw-stat ([a-z-]+)"[^>]*><b>([^<]*)</b><span class="qw-sub">([^<]*)</span>', row)
            self.assertEqual([s[0] for s in stats], ["qw-odds", "qw-runs", "qw-ttf", "qw-kph"], row[:400])
            self.assertTrue(all(s[1] and s[2] for s in stats), "a number without its subtitle: %r" % stats)
            self.assertEqual(stats[0][2], "odds a run", "the odds column mixes units: %r" % stats[0][2])

    def test_the_per_kill_places_are_their_own_section(self):
        g = self.o["grid"]
        i = g.index('<div class="qw-also">')
        self.assertLess(g.index('<div class="qw-grid">'), i)
        # REG-3305 - the heading itself, both ends from the markup (a fixed 200-character window was a guess about its
        # length, and test_a_source_window_must_reach_its_subject counted it: 45 over its ceiling of 44)
        h = g.index('<div class="qw-also-h">', i)
        self.assertIn("priced per kill", g[h:g.index("</div>", h)])
        self.assertIn("Normal The Cow King", g[i:])
        self.assertIn("art/hellbovine_graphic.png", g[i:], "the Cow King's row lost its picture")
        self.assertNotIn("Normal The Cow King", g[:i], "a per-kill place sat among the ranked rows")


class EveryMissingUniqueIsAQuickWin(unittest.TestCase):
    """REG-3290 (his ask 2026-11-06, a screenshot: Quick wins 3 beside All missing 8 - "8 items need to be for quick runs
    im missing 8 so they each need to render their data from where to farm and everything")."""

    def test_the_list_is_every_missing_unique_fastest_first(self):
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
            page = fh.read()
        a = page.index("  window.funiScan=function(){")
        b = page.index("    return { total:items.length, found:found, missing:missing, runs:runs, low:low,", a)
        body = re.sub(r"/\*.{0,6000}?\*/", "", page[a:b], flags=re.S)
        body = "\n".join(l.split("//", 1)[0] for l in body.split("\n"))
        self.assertEqual(body.count("var low=missing.slice()"), 1, "the quick-wins list is not built from every missing unique")
        self.assertNotRegex(body, r"var low=missing\.filter", "the quick-wins list filters the missing uniques again")
        self.assertIn(".sort(function(a,b){ return a._qh-b._qh", body, "the list is not ordered fastest first")

class TheDoctorWatchesThePictures(unittest.TestCase):
    """REG-3269's watcher: an art clean-up that removes a picture the grid names must read MISSING, never ok."""

    def test_a_missing_picture_reads_missing(self):
        from unittest import mock
        sys.path.insert(0, HERE)
        import console_doctor as CD
        state, why = CD._check_quick_wins_places_have_their_pictures()
        self.assertEqual(state, CD.OK, why)
        real = os.path.isfile
        with mock.patch.object(CD.os.path, "isfile", lambda p: False if p.endswith("Coldcrow.gif") else real(p)):
            state, why = CD._check_quick_wins_places_have_their_pictures()
        self.assertEqual(state, CD.MISSING, "a picture the grid names went missing and the doctor said %r" % why)
        self.assertIn("Coldcrow.gif", why)

    def test_a_missing_boss_portrait_reads_missing(self):
        """REG-3278 (the Grok CLI on v3874) - a tile uses BOSS_PORTRAIT first; its files were never checked."""
        from unittest import mock
        sys.path.insert(0, HERE)
        import console_doctor as CD
        real = os.path.isfile
        with mock.patch.object(CD.os.path, "isfile", lambda p: False if p.endswith("Andariel_graphic.png") else real(p)):
            state, why = CD._check_quick_wins_places_have_their_pictures()
        self.assertEqual(state, CD.MISSING, "Andariel's portrait went missing and the doctor said %r" % why)
        self.assertIn("Andariel_graphic.png", why)

    def test_a_zone_table_that_will_not_parse_still_names_a_missing_monster(self):
        """REG-3278 - the zone parse failed first and returned UNKNOWN over a monster file already known gone."""
        from unittest import mock
        sys.path.insert(0, HERE)
        import console_doctor as CD
        real_open, real_isfile = open, os.path.isfile
        page = real_open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
        i = page.index("var TZ_INFO = {") + len("var TZ_INFO = {")
        broken = page[:i] + "'not json'," + page[i:]

        def fake_open(path, *a, **k):
            if str(path).endswith("bible.html"):
                import io as _io
                return _io.StringIO(broken)
            return real_open(path, *a, **k)
        with mock.patch("builtins.open", fake_open):
            state, why = CD._check_quick_wins_places_have_their_pictures()
            self.assertEqual(state, CD.UNKNOWN, "premise: a table that will not parse is UNKNOWN when nothing is gone: %r" % why)
            with mock.patch.object(CD.os.path, "isfile", lambda p: False if p.endswith("Coldcrow.gif") else real_isfile(p)):
                state, why = CD._check_quick_wins_places_have_their_pictures()
        self.assertEqual(state, CD.MISSING, "a missing monster hid behind the zone table's parse error: %r" % why)
        self.assertIn("Coldcrow.gif", why)


RED_PROOF = [
    {'why': "REG-3290 - Pindleskin's place (his loc leads with the Red Portal) draws no zone art",
     'file': 'bible.html',
     'find': '    \'Red Portal by Anya\': "Nihlathak\'s Temple" };',
     'replace': '    \'Red Portal by Anya (unmapped)\': "Nihlathak\'s Temple" };',
     'matches': 1},
    {"why": "REG-3290 - Quick wins hides every missing unique above qlvl 35 again (3 of his 8)",
     "file": "bible.html",
     "find": "    var low=missing.slice()\n",
     "replace": "    var low=missing.filter(function(x){ return (x.qlvl||99)<=35; })\n",
     "matches": 1},
    {"why": "REG-3278 - the boss portraits a tile uses first are never checked",
     "file": "tv/console_doctor.py",
     "find": "    mon = sorted(set(\"art/\" + f for f in files + bosses))\n",
     "replace": "    mon = sorted(set(\"art/\" + f for f in files))\n",
     "matches": 1},
    {"why": "REG-3278 - a zone table that will not parse hides a missing monster picture",
     "file": "tv/console_doctor.py",
     "find": "    except ValueError:\n        if gone_mon:\n",
     "replace": "    except ValueError:\n        if False:\n",
     "matches": 1},
    {"why": "REG-3269 - the doctor reads ok while a picture the Quick wins grid names is gone from art/",
     "file": "tv/console_doctor.py",
     "find": "    if gone:\n        return MISSING, \"%d of the %d pictures the Quick wins grid names are not in art/: %s\" % (\n",
     "replace": "    if False:\n        return MISSING, \"%d of the %d pictures the Quick wins grid names are not in art/: %s\" % (\n",
     "matches": 1},
    {"why": "#85 - the odds column says 'a kill' on a boss row beside 'a run' on an area row again",
     "file": "bible.html",
     "find": "      : _qwStat(fmtOdds(p.chance), 'odds a run', 'qw-odds', 'one run of this place is one kill');",
     "replace": "      : _qwStat(fmtOdds(p.chance), 'odds a kill', 'qw-odds', '');",
     "matches": 1, "needs": "node"},
    {"why": "#85 - Radament's sewers read as Kurast's (act 3) art",
     "file": "bible.html",
     "find": "'Sewers Level 3': 'Lut Gholein Sewers',",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#85 - a boss whose area says 'L3' (Mephisto's Durance of Hate) wears no zone art",
     "file": "bible.html",
     "find": "a.replace(/\\s+(Level\\s+\\d+|L\\d+(-L?\\d+)?)$/i, '')",
     "replace": "a.replace(/\\s+Level\\s+\\d+$/i, '')",
     "matches": 1, "needs": "node"},
    {"why": "#85 - a super-unique's picture names a file that is not in art/",
     "file": "bible.html",
     "find": "su_coldcrow: 'Coldcrow.gif'",
     "replace": "su_coldcrow: 'Coldcrow_gone.gif'",
     "matches": 1, "needs": "node"},
    {"why": "#85 - a ranked row loses the subtitle under its time",
     "file": "bible.html",
     "find": "'time for a 50% chance', 'qw-ttf',",
     "replace": "'', 'qw-ttf',",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
