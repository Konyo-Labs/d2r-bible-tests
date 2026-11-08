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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING on a non-UTF-8 console
    _enable()
except Exception:
    pass
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
  out.tiles[id] = _qwTile(id, T.a, T.n, T.n);   // REG-3321 - the page passes the plain name for the hover
  out.zones[id] = _qwZoneArt(T.a);
});
CFG.bossIds.forEach(function(id){ var a = _qwAreaOf(id, ''); out.bossZones[id] = [a, _qwZoneArt(a), _qwTile(id, a, id)]; });
out.sewers = _qwZoneArt('Sewers Level 3');
out.durance = _qwZoneArt('Durance of Hate L3');
var places = [
  { label: 'Normal Coldcrow', area: 'Cave Level 1', s: { bossId: 'su_coldcrow', name: 'Coldcrow' }, chance: 307, runs: 213, hours: 2.5, kph: 84, kpr: 1, est: true, kind: 'superunique' },
  { label: 'Normal Andariel', area: '', s: { bossId: 'andariel' }, chance: 741, runs: 514, hours: 4.8, kph: 108, kpr: 1, est: false, kind: 'boss' },
  { label: 'Normal The Pit', area: '', s: { bossId: 'pit' }, chance: 87700, runs: 553, hours: 10, kph: 54, kpr: 110, est: false, kind: 'area' },
  { label: 'Normal Pitspawn Fouldog', area: 'Jail Level 2', s: { bossId: 'su_pitspawnfouldog', name: 'Pitspawn Fouldog' }, chance: 1000, runs: 699, hours: 9.7, kph: 72, kpr: 1, est: true, kind: 'superunique' }
];
var also = [ { id: 'su_thecowking', name: 'The Cow King', who: 'Normal The Cow King', area: 'The Secret Cow Level', kind: 'once', chance: 312 },
             { name: 'The Banished', who: 'Normal The Banished', area: 'Catacombs Level 3', kind: 'unique', chance: 603 } ];
out.grid = _qwGridHtml(places, also);
out.gridNoAlso = _qwGridHtml(places, []);
// v3884 (his 11-08: "bosses and other places top 5") - six boss runs draw the best five
out.gridSixBoss = _qwGridHtml([1, 2, 3, 4, 5, 6].map(function(i){ return { label: 'Hell Boss' + i, area: '', s: { bossId: 'andariel' }, chance: 1000 * i, runs: 700 * i, hours: 7 * i, kph: 100, kpr: 1, est: false, kind: 'boss' }; }), []);
out.gridNoBoss = _qwGridHtml(places.filter(function(p){ return p.kind !== 'boss'; }), also);
out.gridDupArea = _qwGridHtml(places.concat([{ label: 'NM The Pit', area: '', s: { bossId: 'pit' }, chance: 90000, runs: 900, hours: 12, kph: 50, kpr: 110, est: false, kind: 'area' }]), also);
out.gridSix = _qwGridHtml(places, also.concat([1, 2, 3, 4].map(function(k){ return { name: 'Pack ' + k, who: 'Hell Pack ' + k, area: 'Somewhere', kind: 'champion', chance: 700 + k }; })));
// v3887 (#161) - the three spearwomen packs: the loop each draws is read off the one map
out.gridLancer = _qwGridHtml([], [{ name: 'Dark Lancer', who: 'Hell Dark Lancer', area: 'Tamoe Highland', kind: 'champion', chance: 900 },
                                  { name: 'Black Lancer', who: 'Hell Black Lancer', area: 'Tamoe Highland', kind: 'champion', chance: 901 },
                                  { name: 'Dark Spearwoman', who: 'Hell Dark Spearwoman', area: 'Tamoe Highland', kind: 'champion', chance: 902 }]);
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
        # v3886 (#150) - the grid ranks through the page's ONE ranking and its two lists (_qwRank, _qwLists, beside _qwPlaces)
        grid = _cut(src, "  function _qwRank(out){", "  window._qwPlaces = _qwPlaces;", keep_end=False) + "\n" + grid
        odds = _cut(src, "  function fmtOdds(c){", "\n")                      # the page's own 1:N formatter
        packs = _cut(src, "const MONSTER_PACK_ART = {", "\n};\n")              # #108 - a random pack's family sprite
        packs += "\n" + _cut(src, "const AREA_RUN_ART = ", "\n")                  # #108 - an area run's own place
        code = "\n".join([tz, key, art, bl.replace("const BOSSES", "var BOSSES", 1), portrait, odds, packs, grid])
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
        crow = re.search(r"su_coldcrow:\s*'([^']+)'", _read()).group(1)
        self.assertIn("art/" + crow, named, "Coldcrow's tile does not carry the picture the page names for him")
        anda = re.search(r"andariel:\s*'([^']+)'", _read()).group(1)   # REG-3321 - the file the page names, never pinned
        self.assertIn("art/" + anda, named, "Andariel's tile does not carry BOSS_PORTRAIT's picture")

    def test_a_per_kill_row_says_what_it_is_and_carries_the_four_columns(self):
        """REG-3325 (#102 - his 11-07 "once? random? i want titles for each one ... also with the odds number of runs"):
        the Cow King's row says 'once a character - each difficulty', a random pack's says what pack it is; each carries
        the ranked rows' four captioned columns, its kills for an even chance computed from its own odds, and the two it
        cannot measure marked so"""
        import math
        g = self.o["grid"]
        also = g[g.index('<div class="qw-also">'):]
        rows = re.findall(r'<div class="qw-row qw-row-also"[^>]*>(.*?)</div>', also)
        self.assertEqual(len(rows), 2, "PREMISE: the fixture's two per-kill places did not draw: %s" % also[:300])
        # #125 + v3886 (#150) - fewest for a 50% chance first, in silospen's All list: Coldcrow (213) 1st, the Cow King
        # (~216 kills) 2nd, The Banished (~418) 3rd
        self.assertIn('<span class="qw-rank">2nd · per kill · once a character · each difficulty</span>', rows[0])
        self.assertIn('<span class="qw-rank">3rd · per kill · random unique pack · spawns by chance</span>', rows[1])
        for row, c in zip(rows, (312, 603)):
            stats = re.findall(r'<span class="qw-stat ([a-z -]+)"[^>]*><b>([^<]*)</b><span class="qw-sub">([^<]*)</span>', row)
            # #109 (his 11-07 order) - kills for an even chance, time, kills an hour, then the odds LAST
            self.assertEqual([x[0].split()[0] for x in stats], ["qw-runs", "qw-ttf", "qw-kph", "qw-odds"], row[:300])
            self.assertEqual(stats[0][1], "~" + format(math.ceil(math.log(0.5) / math.log(1 - 1.0 / c)), ","),
                             "the kills for an even chance are not the per-kill odds' own")
            self.assertEqual(stats[0][2], "kills for a 50% chance")
            self.assertIn("qw-unmeasured", stats[1][0] + stats[2][0])
            self.assertEqual(stats[3][2], "odds a kill", "a per-kill row's odds read as a run's")

    def test_a_monster_tile_draws_the_monster_alone(self):
        """REG-3321 (#102 - his 11-07 "it should render just the monster not the area behind it"): a tile that carries a
        monster has NO zone background and no native title tip over the row; a sprite is drawn as a sprite; a place with no
        monster (an area run) still wears its zone"""
        tiles = list(self.o["tiles"].values()) + [t for (_a, _z, t) in self.o["bossZones"].values()]
        mon = [t for t in tiles if 'class="qw-mon' in t]
        self.assertGreater(len(mon), 20, "PREMISE: too few monster tiles were drawn")
        for t in mon:
            head = t[:t.index(">") + 1]
            self.assertNotIn("background-image", head, "a monster tile paints the zone behind the monster: %s" % head)
            self.assertIn("qw-tile-mon", head)
            self.assertNotIn(" title=", head, "a native title tip still covers the row: %s" % head)
            src = re.search(r'<img class="(qw-mon[^"]*)" src="([^"]+)"', t)
            if "d2mon_" in src.group(2):
                self.assertIn("qw-mon-sprite", src.group(1), "a sprite is not drawn as one: %s" % t[:200])
        pit = self.o["bossZones"].get("pit")
        if pit:
            self.assertIn("background-image", pit[2][:pit[2].index(">") + 1], "an area run lost its zone picture")

    def test_a_random_pack_draws_its_familys_sprite_never_the_zone(self):
        """#108 (his 11-07: "for banished and for pits and for spike freind ... either .gif or a HD extracted art thats related
        and properly matched") - The Banished's row draws the Vampire family's own sprite (The Arreat Summit), not a
        Catacombs tile"""
        # v3887 (#157) - a random pack is in Others and, by its odds, in Combined: one row in each, never in Bosses
        _b, _o, _c = _secs(self.o["grid"])
        self.assertNotIn("Normal The Banished", _b, "a random pack sat in the Bosses list")
        row = [r for r in _o.split('<div class="qw-row') if "Normal The Banished" in r]
        self.assertEqual(len(row), 1, "the Banished row is not in the Others list")
        # v3887 (#158, his 11-08: "for the banished i want this .gif specifically rendering https://d2runewizard.com/monsters/
        # The%20Banished") - its own idle loop (vampire5, the green Banished), not the Vampire family's
        self.assertIn('src="art/d2rw_vampire5.webp"', row[0], "The Banished does not draw the sprite he picked")
        self.assertNotIn("background-image:url(art/tz_", row[0], "a random pack still wears a zone tile")
        self.assertIn("qw-mon-sprite", row[0])

    def test_each_spearwoman_pack_draws_its_own_loop(self):
        """v3887 (#161) - the spearwoman family sprite is 38x120 (the thinnest pack sprite) and read as a dark sliver in a 56px
        tile; each of the three draws its own page's d2runewizard idle loop, never a sibling's colours"""
        for who, f in (("Hell Dark Lancer", "d2rw_cr_lancer3.webp"), ("Hell Black Lancer", "d2rw_cr_lancer4.webp"),
                       ("Hell Dark Spearwoman", "d2rw_cr_lancer1.webp")):
            with self.subTest(who=who):
                row = [r for r in self.o["gridLancer"].split('<div class="qw-row') if who in r]
                self.assertTrue(row, "PREMISE: no %s row was drawn" % who)
                self.assertIn('src="art/%s"' % f, row[0], "%s does not draw its own loop" % who)
                self.assertNotIn("spearwoman.gif", row[0], "%s still draws the thin family sprite" % who)
                self.assertIn("qw-mon-sprite", row[0])

    def test_an_area_run_is_in_neither_list(self):
        """v3886 (#150, his 11-08 "the top 5 when you filter in silopen") - the Cow Level and the Pit as a RUN (~350 / ~110 kills,
        the page's own estimate) are in no silospen list, so neither list draws them, however many variants are on record;
        the per-kill places keep their slots"""
        g = self.o["gridDupArea"]
        pits = [r for r in g.split('<div class="qw-row') if '<b class="qw-name"' in r and 'The Pit</b>' in r]
        self.assertEqual(pits, [], "an area run drew in a silospen list: %d row(s)" % len(pits))
        self.assertIn("Normal The Banished", g, "the per-kill places were pushed off the card")

    def test_every_place_floats_the_consoles_card(self):
        """REG-3321 (#102 - "image cursor floating enlarged ... just like the rest of the console"): a boss the board knows
        floats its boss card (data-boss-tip, an id lookup); a super-unique floats its own sprite by name (data-arttip) - on
        the picture AND on the name"""
        for bid, (_a, _z, t) in self.o["bossZones"].items():
            self.assertIn('data-boss-tip="%s"' % bid, t[:t.index(">") + 1], "boss %s floats no boss card" % bid)
        for tid, t in self.o["tiles"].items():
            if tid.startswith("su_") and tid not in self.o["bossZones"]:
                self.assertIn('data-arttip="%s"' % self.targets[tid]["n"].replace("'", "&#39;"), t[:t.index(">") + 1],
                              "super-unique %s floats no card" % tid)
        g = self.o["grid"]
        self.assertIn('<b class="qw-name" data-arttip="Coldcrow">', g, "a row's NAME floats no card")
        self.assertIn('<b class="qw-name" data-boss-tip="andariel">', g, "a boss row's NAME floats no boss card")
        # REG-3336 - the boss card is the rich one, whose picture frame is an item portrait (52x78): a sprite is enlarged
        # to the plain card's 96px square there too, and the rule outranks the portrait's (an attribute selector)
        src = _read()
        self.assertIn("#arttip img{display:block;width:96px;height:96px", src, "PREMISE: the plain card's picture is not 96px")
        self.assertIn('#arttip.tip-rich img[src*="d2mon_"]{width:96px;height:96px;object-fit:contain', src,
                      "a monster on the rich boss card is drawn in the 52x78 item frame - Andariel ~40px wide")

    def test_the_sprite_is_never_blended_and_the_item_is_the_title(self):
        """REG-3321 - screen blending made every dark pixel vanish (Talic's armour, the stone through Coldcrow); one rule fits
        every sprite on every surface; the Quick wins card sets the ITEM as its title"""
        src = _read()
        rule = src[src.index(".qw-mon.qw-mon-sprite, :is("):]
        rule = rule[:rule.index("}") + 1]
        self.assertNotIn("mix-blend-mode:screen", rule, "the sprite tile blends again: %s" % rule)
        self.assertIn('img[src*="d2mon_"]{object-fit:contain!important;mix-blend-mode:normal!important', src)
        self.assertIn("'<div class=\"f-card f-step f-atom qw-card\">", src, "the Quick wins card lost its own class")
        self.assertIn("#tab-funi .qw-card{--fs-qw-title:calc(var(--fs-display)*1.2)}", src, "the title's size token is gone")
        self.assertIn("#tab-funi .qw-card .f-atomact .f-rwbig{font-family:var(--serif-display,serif);font-size:var(--fs-qw-title)", src,
                      "the item's name is not set as the card's title")

    def test_the_boss_runs_are_the_best_five(self):
        """v3884 (his 11-08: "bosses and other places top 5") - six boss runs on record draw the best five, in order"""
        g = self.o["gridSixBoss"]
        sec1 = g[:g.index('<div class="qw-also">')]
        labels = re.findall(r"Hell Boss(\d)", sec1)
        self.assertEqual(sorted(set(labels), key=labels.index), ["1", "2", "3", "4", "5"],
                         "the boss runs are not the best five: %s" % labels)
        ranks = re.findall(r'<span class="qw-rank">([^<]*)</span>', sec1)
        self.assertEqual(ranks, ["1st · best run", "2nd", "3rd", "4th", "5th"],
                         "a boss row's rank is not its place (v3884: the 5th read 'undefined' on his pixels): %s" % ranks)

    def test_a_ranked_row_is_a_tile_a_place_and_four_captioned_numbers(self):
        g = self.o["gridNoAlso"]
        # v3887 (#157) - of the four places, the three that are one kill a run are the Combined list's rows (The Pit, an area
        # run, is in no silospen list), and Bosses + Others hold the same three, each in its own kind
        rx = r'<div class="qw-row(?: qw-best| qw-row-area)?">(.*?)</div>'
        b, o, c = _secs(g)
        rows = re.findall(rx, c)
        self.assertEqual(len(rows), 3, "the three per-kill places did not make three Combined rows: %s" % g[:300])
        self.assertEqual(len(re.findall(rx, b)) + len(re.findall(rx, o)), 3, "Bosses + Others do not hold the same three places")
        rows = re.findall(rx, g)
        self.assertIn('<div class="qw-row qw-best">', g, "the best place is not marked")
        for row in rows:
            self.assertEqual(row.count('class="qw-tile'), 1, row[:200])
            stats = re.findall(r'<span class="qw-stat ([a-z-]+)"[^>]*><b>([^<]*)</b><span class="qw-sub">([^<]*)</span>', row)
            # #109 (his 11-07: "first should be how many runs. then ... time for a 50% chance then ... runs an hour ... and
            # the odds should be at the end on the right for last 4th column")
            self.assertEqual([s[0] for s in stats], ["qw-runs", "qw-ttf", "qw-kph", "qw-odds"], row[:400])
            self.assertTrue(all(s[1] and s[2] for s in stats), "a number without its subtitle: %r" % stats)
            self.assertEqual(stats[3][2], "odds a run", "the odds column mixes units: %r" % stats[3][2])

    def test_the_bosses_list_is_bosses_and_the_all_list_is_every_monster(self):
        """v3886 (#150, his 11-08 on Bane Ash: "what the fack is fouldog doing in here ... i want ALL and BOSSES.. and the top 5
        when you filter in silopen") - section 1 is silospen's Monster Type Boss: no super-unique (Coldcrow, Pitspawn Fouldog)
        and no area run in it. Section 2 is Monster Type All, ONE list 1st-5th by the first column (runs or kills for a 50%
        chance), fewest first, the five lowest of every per-kill place - bosses included"""
        g = self.o["grid"]
        sec1, secO, sec2 = _secs(g)   # v3887 (#157) - Bosses | Others | Combined (silospen's All, what section 2 was)
        self.assertIn("Normal Andariel", sec1, "PREMISE: the fixture's boss did not draw in the Bosses list")
        for nm in ("Normal Coldcrow", "Normal Pitspawn Fouldog", "Normal The Pit", "Normal The Cow King"):
            self.assertNotIn(nm, sec1, "%s is not a boss in silospen's list, and sat in the Bosses list" % nm)
        order = [nm for nm in ("Normal Coldcrow", "Normal The Cow King", "Normal The Banished", "Normal Andariel",
                               "Normal Pitspawn Fouldog") if nm in sec2]
        self.assertEqual(order, ["Normal Coldcrow", "Normal The Cow King", "Normal The Banished", "Normal Andariel",
                                 "Normal Pitspawn Fouldog"], "the All list is not every per-kill place, fewest first")
        self.assertEqual([sec2.index(nm) for nm in order], sorted(sec2.index(nm) for nm in order),
                         "the All list is out of order")
        self.assertNotIn("Normal The Pit", sec2, "an area run sat in the All list")
        six = self.o["gridSix"]
        sec2six = _secs(six)[2]
        self.assertEqual(len(re.findall(r'<div class="qw-row qw-row-(?:area|also)"', sec2six)), 5,
                         "the All list holds more or fewer than five places")
        ranks = re.findall(r'<span class="qw-rank">(\d)(?:st|nd|rd|th) · per (run|kill)', sec2six)
        self.assertEqual([r[0] for r in ranks], ["1", "2", "3", "4", "5"], "the All list is not numbered 1st-5th: %r" % ranks)
        firsts = [int(x.replace(",", "")) for x in re.findall(r'<span class="qw-stat qw-runs"[^>]*><b>~([\d,]+)</b>', sec2six)]
        self.assertEqual(len(firsts), 5, "PREMISE: a row in the All list has no count: %r" % firsts)
        self.assertEqual(firsts, sorted(firsts), "the All list is not fewest-first: %r" % firsts)
        self.assertNotIn("Normal Pitspawn Fouldog", sec2six, "a place needing more kills took a faster one's slot")
        nob = self.o["gridNoBoss"]
        self.assertIn("No boss drops it", _secs(nob)[0], "an empty Bosses list said nothing")

    def test_others_is_every_monster_that_is_not_a_boss(self):
        """v3887 (#157, his 11-08: "for the others same thing like bosses top 5.. i dont want to mix things up.. we can have a
        combined from both of them") - three lists, never mixed: Others holds no boss, the Combined list holds both, each 1st-5th"""
        b, o, c = _secs(self.o["grid"])
        for nm in ("Normal Coldcrow", "Normal The Cow King", "Normal The Banished", "Normal Pitspawn Fouldog"):
            self.assertIn(nm, o, "%s is not a boss and is missing from Others" % nm)
        self.assertNotIn("Normal Andariel", o, "a boss sat in the Others list")
        self.assertIn("Normal Andariel", c, "the Combined list lost the boss that ranks in its five")
        heads = re.findall(r'<div class="qw-(?:grid|also)-h">([^<]*)</div>', self.o["grid"])
        self.assertEqual([h.split(" ")[0] for h in heads], ["Bosses", "Others", "Combined"], "the three lists are not named: %r" % heads)
        self.assertEqual(len(re.findall(r'<div class="qw-row', _secs(self.o["gridSix"])[1])), 5, "Others is not five rows")

    def test_the_per_kill_places_are_their_own_section(self):
        g = self.o["grid"]
        i = g.index('<div class="qw-also">')   # v3887 (#157) - the Combined list (silospen's All); Others sits before it
        self.assertLess(g.index('<div class="qw-grid">'), i)
        # REG-3305 - the heading itself, both ends from the markup (a fixed 200-character window was a guess about its
        # length, and test_a_source_window_must_reach_its_subject counted it: 45 over its ceiling of 44)
        h = g.index('<div class="qw-also-h">', i)
        self.assertIn("Monster Type: All", g[h:g.index("</div>", h)], "section 2 does not say it is silospen's All list")
        self.assertIn("fewest kills for a 50% chance first", g[h:g.index("</div>", h)])
        h1 = g.index('<div class="qw-grid-h">')
        self.assertLess(h1, g.index('<div class="qw-grid">'))
        self.assertIn("Monster Type: Boss", g[h1:g.index("</div>", h1)], "section 1 does not say it is silospen's Boss list")
        self.assertIn("Normal The Cow King", g[i:])
        # #89 - the picture the page's own map names for him (a pinned file name broke when his sprite became the shared one)
        cow = re.search(r"su_thecowking:\s*'([^']+)'", _read()).group(1)
        self.assertIn("art/" + cow, g[i:], "the Cow King's row lost its picture")
        self.assertNotIn("Normal The Cow King", _secs(g)[0], "a per-kill place sat among the Bosses")


def _secs(g):
    """v3887 (#157) - the card's three lists, each cut by its own heading: Bosses | Others | Combined (silospen's All)."""
    o, c = g.index('<div class="qw-also qw-others">'), g.index('<div class="qw-also"><div class="qw-also-h">Combined')
    return g[:o], g[o:c], g[c:]


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

class AnItemWithNoPlaceSaysWhereItComesFrom(unittest.TestCase):
    """REG-3303 (#85) - silospen gives no monster for Annihilus and the six Colossal jewels, so Quick wins has no place to
    rank for them and their cards fell to "no verified source - drops broadly", which is false for every one: Annihilus is
    Uber Diablo's, the Torch Uber Tristram's, each jewel the Colossal Ancient its own table names. Driven in node from the
    page's _srcNote, COLOSSAL_JEWELS and SPECIAL_DROPS."""

    def test_every_event_item_without_a_place_names_its_real_source(self):
        if not NODE:
            self.skipTest("no node - the page's _srcNote is not driven here (UNMEASURED)")
        src = _read()
        places = _table(src, "QW_PLACES")
        code = (_cut(src, "const COLOSSAL_JEWELS = [", "];") + "\n"
                + _cut(src, "  function _srcNote(n){", "  window._srcNote=_srcNote;"))
        ev = _cut(src, "  uberCharm: {", "  },", keep_end=False)
        event = re.findall(r'\{n: "([^"]+)", from: \["([^"]+)"', ev)
        self.assertGreaterEqual(len(event), 2, "PREMISE: the page's Uber Charms table names no items")
        prog = ("var window = { SUNDER_CHARMS: [], _regKey: function(n){ return String(n || '').toLowerCase(); } };\n"
                + code + "\n"
                + "var out = {}; COLOSSAL_JEWELS.forEach(function(j){ out[j.n] = [_srcNote(j.n), j.ancient]; });\n"
                + "%s.forEach(function(e){ out[e[0]] = [_srcNote(e[0]), e[1]]; });\n" % json.dumps(event)
                + "process.stdout.write(JSON.stringify(out));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        out = json.loads(r.stdout)
        self.assertEqual(len([n for n in out if n not in dict(event)]), 6, "PREMISE: the page names six Colossal jewels")
        missing, wrong = [], []
        for name, (note, source) in sorted(out.items()):
            if name in places:
                continue                      # a place to farm: the grid speaks for it
            if not note or not note.get("t"):
                missing.append(name)
                continue
            key = source if name not in dict(event) else source.split(" (")[0].replace(" completion", "")
            if key.split()[-1].lower() not in note["t"].lower():
                wrong.append("%s: %r does not name %r" % (name, note["t"], key))
        self.assertEqual(missing, [], "these have no place to farm and their card says 'drops broadly': %s" % missing)
        self.assertEqual(wrong, [], "\n".join(wrong))


class OneMonsterOnePicture(unittest.TestCase):
    """#89 / #91 (his 11-06 asks: "a .GIF for coldcrow just like it is here" ... "unified across the platform and rendering
    the same") - a super-unique's Quick wins tile and every artUrl/artOr surface draw ONE file: _QW_SU_ART names, for each
    id, exactly the file D2IO_ART names for that monster's name. Each sprite's source is recorded in
    tv/data/monster_art_fandom.json, and every recorded file is in art/."""

    def test_quick_wins_and_the_board_name_the_same_file(self):
        src = _read()
        targets = json.loads(re.search(r"QW_TARGETS\s*=\s*(\{.*?\});", src, re.S).group(1))
        su = dict(re.findall(r"(su_\w+):\s*'([^']+)'", re.search(r"var _QW_SU_ART = \{(.*?)\};", src, re.S).group(1)))
        i = src.index("const D2IO_ART = {")
        d2 = dict(re.findall(r'^\s*"([^"]+)":\s*"art/([^"]+)"', src[i:src.index("\n};", i)], re.M))
        checked, differ = 0, []
        for sid, f in sorted(su.items()):
            name = (targets.get(sid) or {}).get("n")
            if not name or name not in d2:
                continue
            checked += 1
            if d2[name] != f:
                differ.append("%s (%s): Quick wins %s, the board %s" % (sid, name, f, d2[name]))
        self.assertGreaterEqual(checked, 30, "premise: too few monsters are named by both maps (%d)" % checked)
        self.assertEqual(differ, [], "one monster, two pictures:\n  " + "\n  ".join(differ))

    def _sprites(self):
        src = _read()
        i = src.index("const D2IO_ART = {")
        d2 = re.findall(r'^\s*"([^"]+)":\s*"(art/[^"]+)"', src[i:src.index("\n};", i)], re.M)
        return src, d2

    @staticmethod
    def _norm(n):
        n = re.sub(r"[^a-z]", "", n.lower())
        return n[3:] if n.startswith("the") else n

    def test_one_monster_is_one_key_whatever_its_case(self):
        """REG-3321 (the Grok CLI, #231 6697191216): "Hephasto the Armorer" (the bind rows, 28 uses) named
        hephasto_graphic.png and "Hephasto The Armorer" (Quick wins) the sprite - artUrl's case fold calls such a pair
        ambiguous and draws nothing. No two art-map keys equal under case may name different files."""
        _src, d2 = self._sprites()
        by = {}
        for k, v in d2:
            by.setdefault(k.lower(), set()).add(v)
        split = dict((k, sorted(v)) for k, v in by.items() if len(v) > 1 and any("d2mon_" in x for x in v))
        self.assertEqual(split, {}, "one monster, two keys, two pictures: %r" % split)

    def test_no_baked_picture_draws_a_monster_off_its_sprite(self):
        """REG-3321 (the same eye): an <img> written into the page bypasses artUrl - the Colossal tiles painted Talic.gif
        while the map named his sprite, and the bind rows Lister's, the Smith's, Shenk's... old files. Every baked <img>
        whose FILE NAME spells a monster that has a sprite draws that sprite (matched by the file's own name, never by
        nearby text)."""
        src, d2 = self._sprites()
        sprites = {}
        for k, v in d2:
            if "d2mon_" in v:
                sprites.setdefault(self._norm(k), v)
        self.assertGreater(len(sprites), 40, "PREMISE: the art map names too few sprites")

        def stem(f):
            t = re.sub(r"(_graphic)?\.(png|gif|jpg)$", "", f.split("/")[-1].lower())
            t = re.sub(r"[^a-z]", "", re.sub(r"-opt$|\d+$", "", t))
            return t[3:] if t.startswith("the") else t
        off = []
        for m in re.finditer(r'<img\b[^>]*\bsrc=["\'](art/[^"\'?]+)', src):
            f = m.group(1)
            if "d2mon_" in f or len(stem(f)) < 4:
                continue
            c = sorted(set(v for n, v in sprites.items() if n == stem(f) or n.startswith(stem(f))))
            if len(c) == 1:
                off.append("line %d: %s (its sprite is %s)" % (src.count("\n", 0, m.start()) + 1, f, c[0]))
        self.assertEqual(off, [], "a baked picture draws a monster off its sprite:\n  " + "\n  ".join(off[:12]))

    def test_every_recorded_sprite_is_shipped_and_sourced(self):
        with io.open(os.path.join(HERE, "data", "monster_art_fandom.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
        self.assertGreaterEqual(len(rec["sprites"]), 40)
        for r in rec["sprites"]:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, r["file"])), "%s's sprite is not in art/" % r["name"])
            self.assertTrue(r.get("url", "").startswith("https://"), "%s's sprite has no source" % r["name"])


class EveryPackAndUberWearsItsOwnSprite(unittest.TestCase):
    """#108 - every random-pack monster Quick wins can list has its family's sprite (The Arreat Summit), each file shipped
    with the sha1 its record holds, and a boss and its uber never share a picture (his: "make sure they are diffrent")."""

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        with io.open(os.path.join(HERE, "data", "monster_art_arreat.json"), encoding="utf-8") as fh:
            cls.rec = json.load(fh)
        cls.packs = json.loads(_cut(cls.src, "const MONSTER_PACK_ART = ", "\n};\n")[len("const MONSTER_PACK_ART = "):].rstrip().rstrip(";"))

    def test_every_pack_monster_on_the_page_has_its_sprite(self):
        places = _table(self.src, "QW_PLACES")
        names = sorted(set(r[0] for p in places.values() for r in p.get("r") or []))
        missing = [n for n in names if n not in self.packs and n not in self.rec["unmatched"]]
        self.assertEqual(missing, [], "a random-pack monster has no sprite and no stated reason: %s" % missing)
        # v3886 (#150) - only a random row that can reach silospen's All top 5 is stored now (silospen_places ALL_REACH), so
        # far fewer pack monsters are named than the three-rows-an-item table's 60+; the floor keeps this from passing empty
        self.assertGreaterEqual(len(names), 20, "premise: the page lists %d pack monsters" % len(names))

    def test_every_sprite_is_shipped_with_its_recorded_sha1(self):
        import hashlib
        bad = []
        for f in sorted(set(self.packs.values())):
            p = os.path.join(ROOT, "art", f)
            want = (self.rec["files"].get(f) or {}).get("sha1")
            got = hashlib.sha1(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else None
            if not want or got != want:
                bad.append((f, want, got))
        self.assertEqual(bad, [], "a pack sprite is missing, unrecorded, or not the file its record names: %s" % bad)
        self.assertTrue(all(v.get("grokCold") for v in self.rec["files"].values()), "a file was wired without its cold look")

    def test_a_boss_and_its_uber_never_share_a_picture(self):
        i = self.src.index("const D2IO_ART = {")
        d2 = dict(re.findall(r'^\s*"([^"]+)":\s*"art/([^"]+)"', self.src[i:self.src.index("\n};", i)], re.M))
        pairs = [("Andariel", "Lilith"), ("Izual", "Uber Izual"), ("Duriel", "Uber Duriel"), ("Mephisto", "Uber Mephisto"),
                 ("Diablo", "Uber Diablo"), ("Baal", "Uber Baal")]
        same = [(a, b, d2.get(a)) for a, b in pairs if d2.get(a) == d2.get(b)]
        self.assertEqual(same, [], "a boss and its uber share one picture: %s" % same)
        self.assertEqual(d2.get("Lilith"), "d2arreat_andariel.gif", "his ruling: Uber Lilith wears the Arreat Summit's Andariel")
        self.assertEqual(d2.get("Andariel"), "d2mon_Andariel.gif", "his ruling: Andariel keeps the gif she had")
        ub = dict(re.findall(r"\{ id:'([a-z\-]+)', name:'[^']+', emoji:'[^']*', art:'([^']+)'", self.src))
        for uid, f in (("lilith", "d2arreat_andariel.gif"), ("uber-duriel", "d2arreat_duriel.gif"), ("izual", "d2arreat_izual.gif")):
            self.assertEqual(ub.get(uid), f, "the uber card %s wears %r" % (uid, ub.get(uid)))


@unittest.skipUnless(NODE, "node is required to drive the page's own per-kill list - UNMEASURED here, not a pass")
class OneMonsterOnSeveralLevelsIsOneRow(unittest.TestCase):
    """#108 (Heaven's Light read "Bone Archer" three times - Jail Level 1, 2 and 3, each 1:42,745) - the page's own _qwAlso,
    driven: one monster at the same odds on several levels is one row naming every level; a different odds stays apart."""

    def test_the_levels_join_in_one_row(self):
        src = _read()
        fn = _cut(src, "  function _qwAlso(x, worst, cap){", "\n  }\n")
        js = ("var mf = 0; " + _cut(src, "  var _QW_DIFF = {", "};") + "\n"   # the page's own map, never a re-typed copy
              "function adjustChance(c){ return c; } function effChance(c){ return c; }\n"
              "var QW_TARGETS = {};\n"
              "var QW_PLACES = {X: {f: [], r: [['Bone Archer', 'hell', 'unique', 'Jail Level 1', 42745], ['Bone Archer', 'hell', 'unique', 'Jail Level 2', 42745],"
              " ['Bone Archer', 'hell', 'unique', 'Jail Level 3', 42745], ['Bone Archer', 'hell', 'champion', 'Barracks', 50000]]}};\n"
              + fn + "\nprocess.stdout.write(JSON.stringify(_qwAlso({n: 'X'}, null, 5)));")
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        rows = json.loads(r.stdout)
        uniq = [x for x in rows if x["kind"] == "unique"]
        self.assertEqual(len(uniq), 1, "one monster at one odds on three levels drew %d rows" % len(uniq))
        self.assertEqual(uniq[0]["area"], "Jail Level 1 · Jail Level 2 · Jail Level 3")
        self.assertEqual(len([x for x in rows if x["kind"] == "champion"]), 1, "a different pack kind was folded in")


class EachColossalJewelNamesTheAncientToHunt(unittest.TestCase):
    """REG-3316 (#90, his 11-06 ask: "which of the three i need to hunt for trying to get a specific one") - a Colossal
    jewel's Quick wins card is a grid row naming the Ancient to kill LAST, with his sprite (the file D2IO_ART names for
    him) and his pair at 50/50. The pairs are the verified ones (the wiki's Colossal Ancients page; Icy Veins and AOEAH):
    Talic - Defender's Fire/Bile, Korlic - Protector's Frost/Stone, Madawc - Guardian's Thunder/Light."""

    PAIRS = {"Defender's Fire": "Talic", "Defender's Bile": "Talic", "Protector's Frost": "Korlic",
             "Protector's Stone": "Korlic", "Guardian's Thunder": "Madawc", "Guardian's Light": "Madawc"}

    def test_each_jewel_row_names_its_ancient_his_sprite_and_the_pair(self):
        if not NODE:
            self.skipTest("no node - the page's row is not driven here (UNMEASURED)")
        src = _read()
        i = src.index("const D2IO_ART = {")
        art = dict(re.findall(r'^\s*"([^"]+)":\s*"([^"]+)"', src[i:src.index("\n};", i)], re.M))
        code = (_cut(src, "const COLOSSAL_JEWELS = [", "];") + "\n"
                + _cut(src, "  function _qwStat(", "\n  }") + "\n"
                + _cut(src, "  function _qwColossalRow(name){", "\n  window._qwColossalRow = _qwColossalRow;", keep_end=False))
        prog = ("var window = {};\nfunction esc(s){ return String(s == null ? '' : s).replace(/[&<>\"']/g, function(c){"
                " return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]; }); }\n"
                "var D2IO_ART = " + json.dumps({k: art[k] for k in ("Talic", "Korlic", "Madawc") if k in art}) + ";\n"
                + code + "\nvar out = {};\n"
                + json.dumps(sorted(self.PAIRS)) + ".forEach(function(n){ out[n] = _qwColossalRow(n); });\n"
                "out.__none = _qwColossalRow('Stormlash');\nprocess.stdout.write(JSON.stringify(out));")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        out = json.loads(r.stdout)
        self.assertEqual(out["__none"], "", "a unique that is not a Colossal jewel drew an Ancient row")
        for jewel, anc in sorted(self.PAIRS.items()):
            row = out[jewel]
            self.assertIn("Kill %s last" % anc, row, "%s's row does not name %s to kill last" % (jewel, anc))
            self.assertIn('src="%s"' % art[anc], row, "%s's row does not show %s's sprite" % (jewel, anc))
            self.assertIn("1:2", row)
            sister = [j for j, a in self.PAIRS.items() if a == anc and j != jewel][0]
            for nm in (jewel, sister):
                self.assertIn(nm.replace("'", "&#39;"), row, "%s's row does not name the pair (%s)" % (jewel, nm))
            self.assertEqual(row.count('class="qw-row'), 1, "the jewel's card is not one grid row")


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
        anda = re.search(r"andariel:\s*'([^']+)'", _read()).group(1)   # REG-3321 - whatever file BOSS_PORTRAIT names
        with mock.patch.object(CD.os.path, "isfile", lambda p: False if p.endswith(anda) else real(p)):
            state, why = CD._check_quick_wins_places_have_their_pictures()
        self.assertEqual(state, CD.MISSING, "Andariel's portrait went missing and the doctor said %r" % why)
        self.assertIn(anda, why)

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
    {"why": "v3887 (#157) - the Others list mixes the bosses back in (his 'i dont want to mix things up')",
     "file": "bible.html",
     "find": "             others: rows.filter(function(r){ return r.kind !== 'boss'; }).slice(0, 5), all: rows.slice(0, 5) };",
     "replace": "             others: rows.slice(0, 5), all: rows.slice(0, 5) };",
     "matches": 1, "needs": "node"},
    {"why": "v3886 (#150) - an area run (the Cow Level, the Pit - the page's own per-run estimate) draws in silospen's lists again",
     "file": "bible.html",
     "find": "    var rows = (qp || []).filter(function(p){ return p && p.kind !== 'area' && !(p.kpr > 1); }).map(function(p){\n",
     "replace": "    var rows = (qp || []).filter(function(p){ return p; }).map(function(p){\n",
     "matches": 1, "needs": "node"},
    {"why": "#108 - one monster at the same odds on three levels draws three rows again",
     "file": "bible.html",
     "find": "        if (_same[k]) { _same[k].area += ' · ' + r[3]; _same[k].areas++; return; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#109 - a ranked row drops its odds column (his order: runs, time, runs an hour, then the odds last)",
     "file": "bible.html",
     "find": "      + odds\n      + '</div>';",
     "replace": "      + '</div>';",
     "matches": 1, "needs": "node"},
    {"why": "#109 - a per-kill row's odds go first again, ahead of the kills for an even chance",
     "file": "bible.html",
     "find": "            + _qwStat(fmtOdds(a.chance), 'odds a kill', 'qw-odds', why) + '</div>';",
     "replace": "            + '</div>';",
     "matches": 1, "needs": "node"},
    {"why": "#108 - a random pack draws its zone tile again instead of its family's sprite",
     "file": "bible.html",
     "find": "    var pk = (!bp && !su && monName && typeof MONSTER_PACK_ART !== 'undefined') ? MONSTER_PACK_ART[monName] : null;",
     "replace": "    var pk = null;",
     "matches": 1, "needs": "node"},
    {"why": "#108 - Uber Duriel wears Duriel's own picture again (his: make sure they are different)",
     "file": "bible.html",
     "find": "  \"Uber Duriel\": \"art/d2arreat_duriel.gif\",",
     "replace": "  \"Uber Duriel\": \"art/d2mon_Duriel.gif\",",
     "matches": 1},
    {"why": "#108 - a pack monster loses its sprite with no stated reason",
     "file": "bible.html",
     "find": "  \"The Banished\": \"d2rw_vampire5.webp\",",   # v3887 (#158) - his pick, the page's own Banished loop
     "replace": "",
     "matches": 1},
    {"why": "v3887 (#161) - Dark Lancer draws the 38x120 family sprite again (a dark sliver in its tile)",
     "file": "bible.html",
     "find": "  \"Dark Lancer\": \"d2rw_cr_lancer3.webp\",\n",
     "replace": "  \"Dark Lancer\": \"d2fam_corrupt_rogue_spearwoman.gif\",\n",
     "matches": 1, "needs": "node"},
    {"why": "v3887 (#161) - Black Lancer borrows Dark Lancer's loop (a sibling's colours)",
     "file": "bible.html",
     "find": "  \"Black Lancer\": \"d2rw_cr_lancer4.webp\",\n",
     "replace": "  \"Black Lancer\": \"d2rw_cr_lancer3.webp\",\n",
     "matches": 1, "needs": "node"},
    {"why": "v3887 (#161) - Dark Spearwoman draws the 38x120 family sprite again",
     "file": "bible.html",
     "find": "  \"Dark Spearwoman\": \"d2rw_cr_lancer1.webp\",\n",
     "replace": "  \"Dark Spearwoman\": \"d2fam_corrupt_rogue_spearwoman.gif\",\n",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - the 5th boss row's rank reads 'undefined' (a four-entry ordinal list)",
     "file": "bible.html",
     "find": "(i === 0 ? '1st \u00b7 best run' : (_QW_NTH[i] || ((i + 1) + 'th')))",
     "replace": "(i === 0 ? '1st \u00b7 best run' : ['1st', '2nd', '3rd', '4th'][i])",
     "matches": 1, "needs": "node"},
    {"why": "v3884 - the boss runs stop at four again (his 'top 5')",
     "file": "bible.html",
     "find": "    return { boss: rows.filter(function(r){ return r.kind === 'boss'; }).slice(0, 5),\n",
     "replace": "    return { boss: rows.filter(function(r){ return r.kind === 'boss'; }).slice(0, 4),\n",
     "matches": 1, "needs": "node"},
    {"why": "v3886 (#150) - a super-unique ranks in the Bosses list again (Pitspawn Fouldog on Bane Ash's - his 'fouldog is garbage')",
     "file": "bible.html",
     "find": "    return { boss: rows.filter(function(r){ return r.kind === 'boss'; }).slice(0, 5),\n",
     "replace": "    return { boss: rows.filter(function(r){ return r.kind !== 'area'; }).slice(0, 5),\n",
     "matches": 1, "needs": "node"},
    {"why": "#101 - the All list is not capped at five again",
     "file": "bible.html",
     "find": "             others: rows.filter(function(r){ return r.kind !== 'boss'; }).slice(0, 5), all: rows.slice(0, 5) };",
     "replace": "             others: rows.filter(function(r){ return r.kind !== 'boss'; }).slice(0, 5), all: rows };",
     "matches": 1, "needs": "node"},
    {"why": "#125 - the lists are not ranked fewest-first again (his 'top 1 ... lowest')",
     "file": "bible.html",
     "find": "    rows = _qwRank(rows);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3336 - a monster on the rich boss card shrinks into the item portrait frame again",
     "file": "bible.html",
     "find": '#arttip.tip-rich img[src*="d2mon_"]{width:96px;height:96px;object-fit:contain;margin:0 auto 5px}\n',
     "replace": "",
     "matches": 1},
    {"why": "REG-3325 - a per-kill row carries one number again (his 'also with the odds number of runs')",
     "file": "bible.html",
     "find": "    return Math.ceil(Math.log(0.5) / Math.log(1 - 1 / n));\n",
     "replace": "    return null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3321 - Hephasto's two spellings name two pictures again",
     "file": "bible.html",
     "find": "\"Hephasto the Armorer\": \"art/d2mon_Hephasto_The_Armorer.gif\"",
     "replace": "\"Hephasto the Armorer\": \"art/hephasto_graphic.png\"",
     "matches": 1},
    {"why": "REG-3321 - a baked Colossal tile paints Talic's old file while the map names his sprite",
     "file": "bible.html",
     "find": "<img class=\"d2art-img\" src=\"art/d2mon_Talic.gif\" alt=\"Talic\"",
     "replace": "<img class=\"d2art-img\" src=\"art/Talic.gif\" alt=\"Talic\"",
     "matches": 1},
    {"why": "REG-3321 - a monster tile paints the zone behind the monster again (his 'messy' tiles)",
     "file": "bible.html",
     "find": "    var mon = bp ? 'art/' + bp : (su ? 'art/' + su : (pk ? 'art/' + pk : null)), zone = mon ? null : (ar ? 'art/' + ar : _qwZoneArt(area));\n",
     "replace": "    var mon = bp ? 'art/' + bp : (su ? 'art/' + su : (pk ? 'art/' + pk : null)), zone = (ar ? 'art/' + ar : _qwZoneArt(area));\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3321 - a place's picture floats no card (his 'image cursor floating enlarged')",
     "file": "bible.html",
     "find": "      + _qwHover(bossId, monName) + ' aria-label=\"' + esc(label + (area ? ' · ' + area : '')) + '\">'\n",
     "replace": "      + ' aria-label=\"' + esc(label + (area ? ' · ' + area : '')) + '\">'\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3321 - the sprite is screen-blended again: dark pixels vanish (Talic in a black square)",
     "file": "bible.html",
     "find": "  width:calc(100% - 8px);height:calc(100% - 8px);object-fit:contain;mix-blend-mode:normal;\n",
     "replace": "  width:calc(100% - 8px);height:calc(100% - 8px);object-fit:contain;mix-blend-mode:screen;\n",
     "matches": 1},
    {"why": "REG-3316 - a Colossal jewel's card stops naming the Ancient to kill last",
     "file": "bible.html",
     "find": "      + '<b class=\"qw-name\" data-arttip=\"' + esc(j.ancient) + '\">Kill ' + esc(j.ancient) + ' last</b>'",
     "replace": "      + '<b class=\"qw-name\" data-arttip=\"' + esc(j.ancient) + '\">Colossal Summit</b>'",
     "matches": 1, "needs": "node"},
    {'why': "REG-3303 - Annihilus's card says 'drops broadly' again (Uber Diablo is the only source)",
     'file': 'bible.html',
     'find': "      if (k===window._regKey('Annihilus')) return {",
     'replace': "      if (k===window._regKey('Annihilus (unmapped)')) return {",
     'matches': 1},
    {'why': "REG-3303 - the six Colossal jewels' cards say 'drops broadly' again (the Colossal Ancient fight is their only source)",
     'file': 'bible.html',
     'find': '.filter(function(j){ return window._regKey(j.n)===k; })[0];',
     'replace': '.filter(function(j){ return false; })[0];',
     'matches': 1},
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
     "find": "su_coldcrow: 'd2mon_Coldcrow.gif'",
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
