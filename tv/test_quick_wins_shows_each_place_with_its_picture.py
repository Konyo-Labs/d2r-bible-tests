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
  { label: 'Normal Coldcrow', area: 'Cave Level 1', s: { bossId: 'su_coldcrow', name: 'Coldcrow' }, chance: 307, runs: 213, hours: 2.5, kph: 84, kpr: 1, est: true },
  { label: 'Normal Andariel', area: '', s: { bossId: 'andariel' }, chance: 741, runs: 514, hours: 4.8, kph: 108, kpr: 1, est: false },
  { label: 'Normal The Pit', area: '', s: { bossId: 'pit' }, chance: 87700, runs: 553, hours: 10, kph: 54, kpr: 110, est: false },
  { label: 'Normal Pitspawn Fouldog', area: 'Jail Level 2', s: { bossId: 'su_pitspawnfouldog', name: 'Pitspawn Fouldog' }, chance: 1000, runs: 699, hours: 9.7, kph: 72, kpr: 1, est: true }
];
var also = [ { id: 'su_thecowking', name: 'The Cow King', who: 'Normal The Cow King', area: 'The Secret Cow Level', kind: 'once', chance: 312 },
             { name: 'The Banished', who: 'Normal The Banished', area: 'Catacombs Level 3', kind: 'unique', chance: 603 } ];
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
        self.assertIn('<span class="qw-rank">once a character · each difficulty</span>', rows[0])
        self.assertIn('<span class="qw-rank">random unique pack · spawns by chance</span>', rows[1])
        for row, c in zip(rows, (312, 603)):
            stats = re.findall(r'<span class="qw-stat ([a-z -]+)"[^>]*><b>([^<]*)</b><span class="qw-sub">([^<]*)</span>', row)
            self.assertEqual([x[0].split()[0] for x in stats], ["qw-odds", "qw-runs", "qw-ttf", "qw-kph"], row[:300])
            self.assertEqual(stats[1][1], "~" + format(math.ceil(math.log(0.5) / math.log(1 - 1.0 / c)), ","),
                             "the kills for an even chance are not the per-kill odds' own")
            self.assertEqual(stats[1][2], "kills for a 50% chance")
            self.assertIn("qw-unmeasured", stats[2][0] + stats[3][0])

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
        # #89 - the picture the page's own map names for him (a pinned file name broke when his sprite became the shared one)
        cow = re.search(r"su_thecowking:\s*'([^']+)'", _read()).group(1)
        self.assertIn("art/" + cow, g[i:], "the Cow King's row lost its picture")
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
    {"why": "REG-3336 - a monster on the rich boss card shrinks into the item portrait frame again",
     "file": "bible.html",
     "find": '#arttip.tip-rich img[src*="d2mon_"]{width:96px;height:96px;object-fit:contain;margin:0 auto 5px}\n',
     "replace": "",
     "matches": 1},
    {"why": "REG-3325 - a per-kill row carries one number again (his 'also with the odds number of runs')",
     "file": "bible.html",
     "find": "    return '~' + Math.ceil(Math.log(0.5) / Math.log(1 - 1 / n)).toLocaleString();\n",
     "replace": "    return '—';\n",
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
     "find": "    var mon = bp ? 'art/' + bp : (su ? 'art/' + su : null), zone = mon ? null : _qwZoneArt(area);\n",
     "replace": "    var mon = bp ? 'art/' + bp : (su ? 'art/' + su : null), zone = _qwZoneArt(area);\n",
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
