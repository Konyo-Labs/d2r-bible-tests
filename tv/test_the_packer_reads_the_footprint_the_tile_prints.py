# -*- coding: utf-8 -*-
"""#275 (REG-2051) - THE MULE PACKER READS THE FOOTPRINT EVERY LOCKER TILE PRINTS; A GUESSED SIZE SAYS SO ON THE CHIP.

GrokBot ticks 416-417 on #230 (v3621): UNI-WEAPONS read "3 items · 12 cells" over three tiles that each said "default
1x2" (6), and UNI-ARMOR "24 cells" over tiles summing to 22 - "the chip looks like items x 4". MEASURED at HEAD: the
packer (vaultSize, behind the chip, the gauge and the mule window) carried its OWN keyword table whose unknown-base
default was [2,2], while the tile prints _itemCells (unknown base -> a 1x2 marked approx; EXTRA_ITEMS.cells honoured;
the v2240 plural and v2242 claw fixes). Two copies of one rule, and they disagreed.

  * vaultSize answers exactly what _itemCells answers - an unknown base, an explicit EXTRA_ITEMS size, a known base;
  * the locker chip says how many of its items are of unknown size, counted at the default.
Drives the SHIPPED vaultSize and _itemCells, cut from bible.html and run in node with the catalogues stubbed. A missing
node raises; this law does not skip.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
# v3766 — the class rule moved into _runewordCells, which _itemCells calls. A cut of
# _itemCells alone sizes every runeword by the keyword table (Hand of Justice as gloves).
CELLS_START = "function _itemCells(name){\n"
CELLS_END = "\n  return cells;\n}\n"
RW_START = "function _runewordCells(name){\n"
RW_END = "\n  return cells;\n}\n"
SIZE_START = "  function vaultSize(name){\n"
SIZE_END = "\n  }\n"
CHIP = "(_approxN ? ' (' + _approxN + ' of unknown size, counted at the default 1x2)' : '')"


def _src():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def _cut(s, start, end):
    if s.count(start) != 1:
        raise AssertionError("anchor %r matched %d times - re-point this law" % (start[:40], s.count(start)))
    i = s.index(start)
    return s[i:s.index(end, i) + len(end)]


def _program(prelude, tail):
    if NODE is None:
        raise AssertionError("node is not on this machine - this gate does not skip")
    s = _src()
    # The footprint is measured. This stub is the shape of that measurement: Enigma's legal
    # bases agree, Delirium's agree, and Spirit / Hand of Justice / Grief disagree until the
    # preferred bases, which then span two item types. Enigma has no preferred rescue, so
    # dropping the agreeing-bases return puts it back on the guess.
    stub = r"""
if (typeof window === "undefined") { var window = {}; }
var _savedFoot = window._cbFoot;
var _RW_STUB_IT = [
  ["e", "Enigma", "r"], ["d", "Delirium", "r"], ["s", "Spirit", "r"],
  ["h", "Hand of Justice", "r"], ["g", "Grief", "r"]
];
var _RW_STUB_CODES = {
  Enigma: ["arch"], Delirium: ["helm"], Spirit: ["mon", "crs", "big"],
  "Hand of Justice": ["pb", "ba", "pole"], Grief: ["pb", "ba", "long"]
};
var _RW_STUB_FOOT = { arch:[2,3], helm:[2,2], mon:[2,3], crs:[2,3], big:[2,4], pb:[2,3], ba:[2,3], pole:[2,4], long:[2,4] };
var _RW_STUB_TYPE = { arch:"tors", helm:"helm", mon:"shie", crs:"swor", big:"shie", pb:"swor", ba:"axe", pole:"pole", long:"swor" };
var _RW_STUB_NAME = { arch:"Archon Plate", helm:"Bone Visage", mon:"Monarch", crs:"Crystal Sword", big:"Tower Shield", pb:"Phase Blade", ba:"Berserker Axe", pole:"Thresher", long:"Colossus Blade" };
window._cbDb = function(){
  var b = {};
  Object.keys(_RW_STUB_FOOT).forEach(function(c){
    var row = [];
    row[0] = _RW_STUB_NAME[c]; row[1] = _RW_STUB_TYPE[c];
    row[15] = _RW_STUB_FOOT[c][0]; row[16] = _RW_STUB_FOOT[c][1];
    b[c] = row;
  });
  return { it: _RW_STUB_IT, b: b };
};
window._cbBasesOf = function(it){ return (_RW_STUB_CODES[it && it[1]] || []).slice(); };
window._cbFoot = function(e){
  if (_savedFoot){ var prev = _savedFoot(e); if (prev) return prev; }
  var f = e && _RW_STUB_FOOT[e.base];
  return f ? [f[0], f[1]] : null;
};
var RW_BIS = {
  Spirit: { b: ["Monarch", "Crystal Sword"] },
  "Hand of Justice": { b: ["Phase Blade", "Berserker Axe"] },
  Grief: { b: ["Phase Blade", "Berserker Axe"] }
};
"""
    body = stub + """
var EXTRA_ITEMS = { "Odd Trophy": { base: "Mystery Base", cells: { w: 2, h: 4 } } };
var ITEM_CODEX = { "Rainbow Facet": { rarity: "unique", base: "Jewels" }, "Bartuc's Cut-Throat": { base: "Greater Talons" },
                   "Shaftstop": { base: "Mesh Armor" }, "Nosferatu's Coil": { base: "Vampirefang Belt" } };
var ITEM_TIP = {};
var RUNEWORD_TIP = { "Enigma": { t: "Runeword", b: "3 socket Body Armor" }, "Spirit": { t: "Runeword", b: "4 socket Swords or Shields" },
                     "Hand of Justice": { t: "Runeword", b: "4 socket Weapons" }, "Delirium": { t: "Runeword", b: "3 socket Helms" },
                     "Grief": { t: "Runeword", b: "5 socket Axes Swords" } };
function findRuneword(n){ return RUNEWORD_TIP[n] ? n : null; }
var SET_SLOTS = { "Tal Rasha's Guardianship": "armor", "Tal Rasha's Horadric Crest": "helm", "Tal Rasha's Adjudication": "amulet",
                  "Cathan's Mesh": "chainmail", "Cow King's Horns": "war bonnet", "Cathan's Rule": "rod" };
function findSetPiece(n){ return SET_SLOTS[n] ? { slot: SET_SLOTS[n] } : null; }
%s
%s
""" % ("var _ITEM_CELLS_CACHE = {};\n" + _cut(s, RW_START, RW_END) + _cut(s, CELLS_START, CELLS_END),
      _cut(s, SIZE_START, SIZE_END))
    return prelude + body + tail


def _node(prelude, tail):
    # the program goes in on STDIN - a law never hands node its program on argv
    r = subprocess.run([NODE, "-"], input=_program(prelude, tail), capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the cut functions did not run in node: %s" % r.stderr[-400:])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _sizes(names, prelude=""):
    tail = """
var OUT = {};
%s.forEach(function(n){ var c = _itemCells(n); OUT[n] = { pack: vaultSize(n), tile: [c.w, c.h], approx: !!c.approx }; });
console.log(JSON.stringify(OUT));
""" % json.dumps(names)
    return _node(prelude, tail)


def _planner(rec_js):
    """A stub of the planner record and the game footprint. The size comes back only for a code this map holds."""
    return """
var REC = %s;
var FOOT = { '7cr': [2, 3], '7gd': [2, 4] };
var window = {
  _vpMadeOf: function(n){
    var r = REC[n];
    return r ? { base: r.base, q: r.q, baseName: r.baseName, id: r.id } : null;
  },
  _cbFoot: function(e){
    var f = e && FOOT[e.base];
    return f ? [f[0], f[1]] : null;
  }
};
""" % rec_js


class ThePackerReadsTheFootprintTheTilePrints(unittest.TestCase):

    NAMES = ["Some Unheard-Of Thing", "Odd Trophy", "Rainbow Facet", "Bartuc's Cut-Throat", "Shaftstop",
             "Nosferatu's Coil", "Annihilus", "Gheed's Fortune"]

    def test_the_packer_and_the_tile_agree_on_every_kind_of_name(self):
        got = _sizes(self.NAMES)
        for n in self.NAMES:
            self.assertEqual(got[n]["pack"], got[n]["tile"],
                             "%s: the packer packs %r while its tile prints %r" % (n, got[n]["pack"], got[n]["tile"]))

    def test_a_magic_or_rare_cell_is_sized_by_its_base_not_a_flat_2x1(self):
        """REG-2193 — the MAGIC & RARE locker cell hardcoded `grid-column:span 2;grid-row:span 1`, so a rare
        Jewel, Ring or Small Charm drew 2x1 and a Grand Charm 2x1 instead of their real 1x1 / 1x3 (GrokBot saw
        it on his live board). The cell now sizes from the SAME _itemCells the catalogue cells use — one
        footprint source — so the Tetris-fit counts real cells. [[copy-drift]] (REG-2051 missed this path)."""
        got = _sizes(["Jewel", "Ring", "Small Charm", "Grand Charm", "Large Charm"])
        self.assertEqual(got["Jewel"]["tile"], [1, 1])
        self.assertEqual(got["Ring"]["tile"], [1, 1])
        self.assertEqual(got["Small Charm"]["tile"], [1, 1])
        self.assertEqual(got["Grand Charm"]["tile"], [1, 3])
        self.assertEqual(got["Large Charm"]["tile"], [1, 2])
        src = _src()
        self.assertIn("var _mf = (typeof _itemCells === 'function') ? _itemCells(base || n)", src,
                      "the magic/rare cell must size from _itemCells (REG-2193)")
        self.assertIn("grid-column:span '+_mf.w+';grid-row:span '+_mf.h+'", src,
                      "the magic/rare cell must span its real footprint (REG-2193)")
        self.assertNotIn("grid-column:span 2;grid-row:span 1;border-color:", src,
                         "the magic/rare cell must not hardcode a 2x1 span (REG-2193)")

    def test_an_unknown_base_packs_at_the_default_the_tile_names(self):
        got = _sizes(["Some Unheard-Of Thing"])["Some Unheard-Of Thing"]
        self.assertTrue(got["approx"], "premise: an unheard-of base is a guessed size")
        self.assertEqual(got["pack"], [1, 2], "an unknown base packs at a size its tile does not print: %r" % got)

    def test_an_explicit_size_is_honoured_by_the_packer(self):
        self.assertEqual(_sizes(["Odd Trophy"])["Odd Trophy"]["pack"], [2, 4])

    def test_a_runeword_is_sized_by_its_base_never_by_its_name(self):
        got = _sizes(["Enigma", "Delirium", "Spirit", "Hand of Justice"])
        self.assertEqual((got["Enigma"]["tile"], got["Enigma"]["approx"]), ([2, 3], False),
                         "Enigma (3 socket Body Armor) is not drawn as the body armour it always is: %r" % got["Enigma"])
        self.assertEqual((got["Delirium"]["tile"], got["Delirium"]["approx"]), ([2, 2], False), got["Delirium"])
        self.assertTrue(got["Spirit"]["approx"], "a runeword whose base names two classes was given a size: %r" % got["Spirit"])
        self.assertTrue(got["Hand of Justice"]["approx"],
                        "a runeword was sized by a keyword in its NAME (Hand -> gloves): %r" % got["Hand of Justice"])
        for n in got:
            self.assertEqual(got[n]["pack"], got[n]["tile"], n)

    def test_a_runeword_with_no_stored_base_stays_a_guess(self):
        """Grief's tip names axes and swords. With no planner base, that is still a guess, and a
        Phase Blade is not invented from the word."""
        got = _sizes(["Grief"])["Grief"]
        self.assertTrue(got["approx"], "Grief with no planner base was given a size: %r" % got)
        self.assertEqual(got["pack"], [1, 2], got)
        self.assertEqual(got["pack"], got["tile"], got)

    def test_a_stored_phase_blade_occupies_six_cells_and_the_packer_agrees(self):
        """The shared stash asks vaultSize, which asks _itemCells. A stored Phase Blade (code 7cr)
        is 2 wide by 3 tall. That is the 6 cells. Every other page uses the same packer."""
        prelude = _planner(
            '{ Grief: { base: "7cr", q: "r", baseName: "Phase Blade", id: "grief" },'
            ' "Odd Trophy": { base: "7cr", q: "r", baseName: "Phase Blade", id: "odd" } }')
        got = _sizes(["Grief", "Spirit", "Hand of Justice", "Enigma", "Delirium", "Odd Trophy"], prelude)
        g = got["Grief"]
        self.assertEqual(g["tile"], [2, 3], "a stored Phase Blade was not 2 wide by 3 tall: %r" % g)
        self.assertFalse(g["approx"], "a measured footprint was marked as a guess: %r" % g)
        self.assertEqual(g["pack"], g["tile"], g)
        self.assertEqual(g["tile"][0] * g["tile"][1], 6, g)
        self.assertTrue(got["Spirit"]["approx"], "Spirit was given a size with no stored base: %r" % got["Spirit"])
        self.assertTrue(got["Hand of Justice"]["approx"], got["Hand of Justice"])
        self.assertEqual((got["Enigma"]["tile"], got["Enigma"]["approx"]), ([2, 3], False), got["Enigma"])
        self.assertEqual((got["Delirium"]["tile"], got["Delirium"]["approx"]), ([2, 2], False), got["Delirium"])
        self.assertEqual((got["Odd Trophy"]["tile"], got["Odd Trophy"]["approx"]), ([2, 4], False),
                         "an explicit cell size lost to the planner base: %r" % got["Odd Trophy"])
        bare = _sizes(["Grief"], _planner("{}"))
        self.assertTrue(bare["Grief"]["approx"],
                        "Grief was sized from the word while the game table sat unused: %r" % bare["Grief"])
        self.assertEqual(bare["Grief"]["pack"], [1, 2], bare["Grief"])

    def test_a_changed_base_does_not_keep_the_old_rectangle(self):
        """The first answer is cached. A different stored code, a cleared record, and a code the
        table does not size must each be asked again. A missing measurement stays a guess."""
        tail = """
var OUT = {};
function snap(k){
  var c = _itemCells('Grief');
  OUT[k] = { pack: vaultSize('Grief'), tile: [c.w, c.h], approx: !!c.approx };
}
snap('phase');
REC.Grief = { base: '7gd', q: 'r', baseName: 'Colossus Blade', id: 'grief' };
snap('colossus');
delete REC.Grief;
snap('cleared');
REC.Grief = { base: 'missing', q: 'r', baseName: 'Nope', id: 'grief' };
snap('unknown');
console.log(JSON.stringify(OUT));
"""
        got = _node(_planner('{ Grief: { base: "7cr", q: "r", baseName: "Phase Blade", id: "grief" } }'), tail)
        self.assertEqual((got["phase"]["tile"], got["phase"]["approx"], got["phase"]["pack"]),
                         ([2, 3], False, [2, 3]), got["phase"])
        self.assertEqual((got["colossus"]["tile"], got["colossus"]["approx"], got["colossus"]["pack"]),
                         ([2, 4], False, [2, 4]), got["colossus"])
        self.assertEqual((got["cleared"]["tile"], got["cleared"]["approx"]), ([1, 2], True), got["cleared"])
        self.assertEqual(got["cleared"]["pack"], got["cleared"]["tile"], got["cleared"])
        self.assertTrue(got["unknown"]["approx"], "a base the table does not size was still drawn: %r" % got["unknown"])
        self.assertEqual(got["unknown"]["tile"], [1, 2], got["unknown"])

    def test_a_set_piece_is_sized_by_its_slot(self):
        """REG-2068 - set pieces carry no codex base; REG-2051 dropped the slot lookup the old packer had, so Tal Rasha's
        Guardianship packed as a guessed 1x2 (Routine I red on v3623, v203_mule_vault:149)."""
        want = {"Tal Rasha's Guardianship": [2, 3], "Tal Rasha's Horadric Crest": [2, 2], "Tal Rasha's Adjudication": [1, 1],
                "Cathan's Mesh": [2, 3], "Cow King's Horns": [2, 2]}
        got = _sizes(sorted(want))
        for n, w in want.items():
            self.assertEqual((got[n]["tile"], got[n]["approx"]), (w, False),
                             "%s: a set piece was not sized by its slot: %r" % (n, got[n]))
            self.assertEqual(got[n]["pack"], got[n]["tile"], n)
        rod = _sizes(["Cathan's Rule"])["Cathan's Rule"]
        self.assertTrue(rod["approx"], "a slot with no settled size (rod) was given one: %r" % rod)

    def test_the_chip_says_how_many_sizes_are_guessed(self):
        s = _src()
        self.assertEqual(s.count(CHIP), 1, "the locker chip no longer says how many of its sizes are guessed")
        self.assertEqual(s.count("var _approxN = items.filter(function(n){ var c = (typeof _itemCells === 'function')"
                                 " ? _itemCells(n) : null; return !!(c && c.approx); }).length;"), 1,
                         "the chip's guessed-size count is no longer asked of _itemCells")

    def test_two_copies_pack_as_two_rectangles_and_a_tile_click_stays(self):
        """Two Griefs on a stored Phase Blade are two 2x3 tiles. One name is one tile.
        The shared-stash tile HTML does not call openDrop. The gold box counts the copies.
        #144.10 shared half (REG-2801): the shared stash is laid by _sharedLayout (the plan's 5 pages) - _sharedPack went
        with the by-slot tabs. How many copies the stash keeps (the war cap) is tv/test_the_shared_stash_draws_the_plans
        _pages.py's subject; here every copy is kept, so the footprint is all this case measures."""
        s = _src()
        pack = _cut(s, "  function packGrid(items, gw, gh, occ){\n",
                    "  try { window._sharedNames = _sharedNames; } catch(e){}\n")
        prelude = _planner('{ Grief: { base: "7cr", q: "r", baseName: "Phase Blade", id: "grief" } }')
        tail = pack + """
function esc(v){ return String(v == null ? '' : v); }
function jsArg(v){ return String(v).replace(/\\\\/g, '\\\\\\\\').replace(/'/g, "\\\\'"); }
function art(){ return '<i class="d2art-wrap"></i>'; }
window._gridFault = function(){ return { fault: false, used: 0, cap: 100, oob: 0, over: 0 }; };
var copies = { Grief: 2 };
function copyCount(n){ var c = copies[n]; return (c && c > 0) ? c : 1; }
function take(list){
  var over = 0, used = 0, seen = {};
  list.forEach(function(it){
    used += it.w * it.h;
    for (var x = 0; x < it.w; x++) for (var y = 0; y < it.h; y++){
      var k = (it.x + x) + ',' + (it.y + y);
      if (seen[k]) over++; else seen[k] = 1;
    }
  });
  return { n: list.length, over: over, used: used,
           tiles: list.map(function(it){ return [it.n, it.w, it.h]; }) };
}
function _muleItemKey(n, ci){ return ci ? n + ' #' + (ci + 1) : n; }
function _shelfCopyCount(n){ return copyCount(n); }
var lay2 = _sharedLayout(['Grief']), two = { placed: lay2.pages[0], left: lay2.left };
copies = { Spirit: 1 };
var lay1 = _sharedLayout(['Spirit']), one = { placed: lay1.pages[0], left: lay1.left };
var html = gridHtml([{ n: 'Grief', x: 0, y: 0, w: 2, h: 3 }], 10, 10, 46);
copies = { Grief: 2 };
var total = (typeof _sharedCopyTotal === 'function') ? _sharedCopyTotal(['Grief']) : null;
console.log(JSON.stringify({ two: take(two.placed), twoLeft: two.left.length, one: take(one.placed),
  openDrop: html.indexOf('openDrop') >= 0, tile: html.indexOf('vd-item') >= 0, total: total }));
"""
        got = _node(prelude, tail)
        self.assertEqual(got["two"]["n"], 2, got["two"])
        self.assertEqual(got["two"]["tiles"], [["Grief", 2, 3], ["Grief", 2, 3]], got["two"])
        self.assertEqual(got["two"]["used"], 12, got["two"])
        self.assertEqual(got["two"]["over"], 0, got["two"])
        self.assertEqual(got["twoLeft"], 0, got)
        self.assertEqual(got["one"]["n"], 1, got["one"])
        self.assertEqual(got["one"]["tiles"], [["Spirit", 1, 2]], got["one"])
        self.assertFalse(got["openDrop"], "the shared-stash tile still opens the item page")
        self.assertTrue(got["tile"], got)
        self.assertEqual(got["total"], 2, got)
        # the window's gold box counts what the layout PLACED - one entry per copy - never the names on a page
        self.assertEqual(s.count("    var pageN = pg.length;\n"), 1, "the shared window no longer counts the copies it placed")
        self.assertEqual(s.count("    var totalAll = lay.pages.reduce(function(a, p){ return a + p.length; }, 0) + lay.left.length;\n"), 1)
        self.assertNotIn("pg.items.length + ' on this page'", s)


RED_PROOF = [
    {"why": "REG-2051 - a runeword falls to the default again although its base settles its size (Enigma 1x2)",
     "file": "bible.html",
     "find": "  if (_same) return { w: _same.w, h: _same.h };\n",
     "replace": "  if (false) return { w: _same.w, h: _same.h };\n",
     "matches": 1},
    {"why": "REG-2051 - a runeword is sized by a keyword in its name again (Hand of Justice read as gloves)",
     "file": "bible.html",
     "find": "        if (_rwSized){ cells = _rwSized; _ITEM_CELLS_CACHE[_ck] = cells; return cells; }\n",
     "replace": "\n",
     "matches": 1},
    {"why": "REG-2051 - the packer answers with its own default again (a second copy of the footprint rule)",
     "file": "bible.html",
     "find": "    return c ? [c.w || 1, c.h || 1] : [1, 2];\n",
     "replace": "    return (c && !c.approx) ? [c.w || 1, c.h || 1] : [2, 2];\n",
     "matches": 1},
    {"why": "REG-2068 - a set piece falls to the guessed 1x2 again (the slot lookup is dropped)",
     "file": "bible.html",
     "find": "if (_spz && _spz.slot) base = String(_spz.slot);",
     "replace": "if (false) base = '';",
     "matches": 1},
    {"why": "REG-2068 - a chainmail set piece (Cathan's Mesh) is a guessed size again",
     "file": "bible.html",
     "find": "|mail|chain ?mail|hauberk|",
     "replace": "|mail|hauberk|",
     "matches": 1},
    {"why": "REG-2051 - the chip stops saying how many sizes are guessed",
     "file": "bible.html",
     "find": "(_approxN ? ' (' + _approxN + ' of unknown size, counted at the default 1x2)' : '')",
     "replace": "''",
     "matches": 1},
    {"why": "two copies of one name pack as one tile again",
     "file": "bible.html",
     "find": "      for (var k = 0; k < cc; k++){\n        var key = _muleItemKey(n, cis[k]), c = _vaultPlanCell(pl, cis[k]);\n",
     "replace": "      for (var k = 0; k < 1; k++){\n        var key = _muleItemKey(n, cis[k]), c = _vaultPlanCell(pl, cis[k]);\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
