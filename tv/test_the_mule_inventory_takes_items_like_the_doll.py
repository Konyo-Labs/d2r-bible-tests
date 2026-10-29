# -*- coding: utf-8 -*-
"""#174 v-B5 — THE MULE WINDOW'S 10x4 INVENTORY TAKES ITEMS LIKE THE DOLL DOES.

GrokBot measured it (ACT 5855160685, v3517, the mule overlay's EQUIPMENT, SETS-REST): the 10x4 grid under the doll was
40 of 40 cells DEAD - a click did nothing. His ask (before Tuesday), Maxroll parity and D2R one-to-one:
  (1) an EMPTY cell opens the SAME item Select the doll's empty slots open (v3515 "one picker, two hosts"), filtered to
      what an inventory takes: charms, jewels, rings and amulets, and anything whose size fits the free space there;
  (2) D2R's sizes - small charm 1x1, large 1x2, grand 1x3, Annihilus 1x1, Hellfire Torch 1x2, Gheed's 1x3, sunders 1x3 -
      placed one-to-one by D2R's grid rules: inside the 10x4, over nothing;
  (3) a FILLED tile shows the game tooltip (the d2Tip / _cbTipEntry path) and can be replaced or removed;
  (4) the placement lands in the store the window already renders (inv.placed through gridHtml) and obeys the vault
      door: a MAIN-locked item is refused and says who holds it, exactly like _mpEqPlace.

What this law holds, each case DRIVEN in node on the SHIPPED code - the vault span (the mule window), the ⟦CHARACTER
BUILDER JS⟧ block, the generated ⟦CB_DB⟧ block and the mule tooltip script, each cut from bible.html by the sibling
laws' own cutters, never re-typed here - on a seeded mule:
  · EVERY EMPTY CELL IS A CONTROL and opens the builder's picker in the MULE host with kind 'inv' on that cell (no
    "In this locker" tab - the locker's rows are already in the grids); a covered cell opens nothing; without the
    builder's block no cell claims to be clickable and the grid says UNKNOWN.
  · THE LIST IS WHAT FITS AN INVENTORY AT THAT CELL: charms, jewels, rings and amulets always; every other item only
    when its size fits there (a Shako at an open cell, never in a 1x1 hole; a 2x4 bow only where four rows are free).
  · A GRAND CHARM LANDS 1x3 ON THE CELL HE CLICKED, drawn there, stored on the mule {page, x, y, w, h, source manual,
    id, base}, and d2r_charBuilds / d2r_cbSel are byte-identical. Every charm takes its size from ONE source - the
    builder's (_cbFoot: the CB_DB base's invwidth x invheight, the game's tables) - and the builder's own inventory reads
    the same one.
  · A PICK THAT DOES NOT FIT IS REFUSED WITH ITS REASON, never moved: past the grid's edge, over a tile placed from the
    database, over a locker item placed there by hand; a replacement that does not fit leaves the tile.
  · A FILLED TILE: a click opens Edit (Change Item, Remove) and shows the builder's in-game box over the STORED entry
    (a runeword on its base - Enigma on Mage Plate - never re-read from the art's name); a hover does the same; replace
    keeps the cell; Remove and Delete take it off. A runeword waits on its Base tab, which lists only bases that fit.
  · A MAIN-LOCKED CHARM IS REFUSED and says which source holds the lock; a free one still lands.
  · THE DOOR FILES A NEW PLACEMENT ONCE (an edit never re-files), and the filed item is ONE item: its database tile is the
    locker's copy of that name, never packed a second time. #174 v-B5 found, building this: the SAME double was live on
    the doll - a database pick filed by the door was worn AND packed in the grid (Tyrael's Might, twice). Fixed and held.
  · Esc closes the host's top layer, then the picker, then the window.
  · THE DOCTOR: a stored record that cannot be laid (off the grid, a size nobody recorded) is a conflict with its reason,
    NOT drawn, said on the window with a way to remove it - its size is UNKNOWN, never a guessed 1x1.

⚠ WHAT THIS LAW CANNOT SEE: pixels and a real pointer - that a real click on a cell reaches it (no tile or overlay over it)
is the mule window's width law's to judge in a browser, and GrokBot's on his screen.
RED_PROOF below.
"""
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_the_mule_picker_offers_the_whole_database as MP  # noqa: E402  the mule host's harness, one cut
import test_the_mule_window_equips_and_says_its_source as EQ  # noqa: E402  the mule harness's pieces
import test_the_character_builder_is_their_builder as CB  # noqa: E402  the builder's cutters
import test_the_character_builder_is_joined_to_the_engine_and_the_mule_window as JN  # noqa: E402  the tooltip script
from test_the_mule_window_is_the_planner_shell import _vault_span, _static_attrs  # noqa: E402

NODE = EQ.NODE
MULE = "uni-armor"


def _harness():
    """the picker law's harness, taught one more thing: document.querySelector answers a database tile of the inventory
    (#vault-detail .vd-item[data-dbkey="K"]) with a stand-in read off the HTML the window drew - so the tile's click can
    show its tooltip the way the page does. Anchored once, so a moved harness fails loudly here."""
    h = MP._harness()
    a = "  querySelector: function(sel){ return sel === '.tab.active' ? { dataset: { tab: 'vault' } } : null; },"
    b = ("  querySelector: function(sel){ if (sel === '.tab.active') return { dataset: { tab: 'vault' } };\n"
         "    var m = /\\.vd-item\\[data-dbkey=\"([^\"]+)\"\\]/.exec(sel); return m ? tileEl(m[1]) : null; },")
    assert h.count(a) == 1, "the mule harness moved - this law's anchor matches %d times" % h.count(a)
    return h.replace(a, b)


HELP = r"""
function invHtml(){ var h = box.innerHTML, i = h.indexOf('<div class="mp-inv">'); return i < 0 ? '' : h.slice(i, h.indexOf('</section>', i)); }
function clickable(){ return (invHtml().match(/<div class="vd-cell" data-cx="/g) || []).length; }
function cellTag(x, y){ var m = new RegExp('<div class="vd-cell" data-cx="' + x + '" data-cy="' + y + '"[^>]*>').exec(invHtml()); return m ? m[0] : null; }
function dbTiles(){ var re = /<div class="vd-item vd-db[^"]*"[^>]*? data-dbkey="([^"]+)" data-n="([^"]*)" data-x="(\d+)" data-y="(\d+)" data-w="(\d+)" data-h="(\d+)"/g, m, o = [];
  var h = invHtml(); while ((m = re.exec(h))) o.push({ key: unesc(m[1]), n: unesc(m[2]), x: +m[3], y: +m[4], w: +m[5], h: +m[6] }); return o; }
function invStore(){ return (eq()['uni-armor'] || {}).inv || {}; }
function invList(){ var s = invStore(); return Object.keys(s).sort().map(function(k){ var e = s[k];
  return { key: k, name: e.name, page: e.page, x: e.x, y: e.y, w: e.w, h: e.h, source: e.source, id: e.id || null, base: e.base || null, at: e.at, ilvl: e.ilvl }; }); }
function keyOf(name){ var k = null; invList().forEach(function(e){ if (e.name === name) k = e.key; }); return k; }
/* THE ROW IS DRIVEN, not a helper beside it: a control's own handler text, read off the HTML the window drew, is run */
function attrOf(tag, name){ var m = new RegExp(' ' + name + '="([^"]*)"').exec(tag || ''); return m ? unesc(m[1]) : null; }
function tileTag(key){ var h = invHtml(), i = h.indexOf('data-dbkey="' + key + '"'); return i < 0 ? null : h.slice(h.lastIndexOf('<div', i), h.indexOf('>', i) + 1); }
function run(code, event){ if (!code) return 'NO HANDLER'; return eval(code); }
function pickAt(x, y, id){ window._mpInvCell(x, y); return window._cbChoose(id); }
/* a base that can drop in more than one quality (a jewel: magic or rare) waits on its Quality tab, as in the builder */
function place(x, y, id){ var ok = pickAt(x, y, id); if (ok && st().pick && st().pick.tab === 'quality') ok = window._cbQuality('m'); return ok; }
function artOf(key){ var h = invHtml(), i = h.indexOf('data-dbkey="' + key + '"'); if (i < 0) return null;
  var m = /class="d2art-wrap[^"]*" role="img" aria-label="([^"]*)"/.exec(h.slice(i)); return m ? unesc(m[1]) : null; }
function baseCodes(){ var re = /data-base="([^"]+)"/g, m, o = [], h = modalHtml() || ''; while ((m = re.exec(h))) o.push(unesc(m[1])); return o; }
function itemsBox(){ var m = /mp-box-k">Items<\/span><span class="mp-box-v"(?: title="[^"]*")?>(\d+)/.exec(box.innerHTML); return m ? +m[1] : null; }
function copiesBox(){ var m = /<span>Copies<\/span><span>(\d+)<\/span>/.exec(box.innerHTML); return m ? +m[1] : null; }
function allTiles(name){
  var ld = window._muleLoad(window._muleNamesFor('uni-armor'), window._mpWornFor('uni-armor', eq()), 'uni-armor'), n = 0;
  ld.mules.forEach(function(m){ m.stash.concat(m.inv).forEach(function(p){ if (p.n === name) n++; });
    Object.keys(m.tabs || {}).forEach(function(t){ m.tabs[t].forEach(function(p){ if (p.n === name) n++; }); }); });
  return { tiles: n, phys: ld.phys, worn: ld.worn };
}
/* a stand-in for a database tile, read off the HTML the window drew (its attributes and its art's name) */
function tileEl(key){
  var h = box.innerHTML, i = h.indexOf('data-dbkey="' + key + '"'); if (i < 0) return null;
  var s = h.lastIndexOf('<div', i), e = h.indexOf('>', i), tag = h.slice(s, e + 1), attrs = {};
  tag.replace(/([\w-]+)="([^"]*)"/g, function(_, k, v){ attrs[k] = unesc(v); return _; });
  var am = /aria-label="([^"]*)"/.exec(h.slice(e + 1, h.indexOf('</div>', e)));
  var art = { getAttribute: function(k){ return k === 'aria-label' && am ? unesc(am[1]) : null; } };
  var el = { nodeType: 1, getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; },
    hasAttribute: function(k){ return Object.prototype.hasOwnProperty.call(attrs, k); },
    setAttribute: function(k, v){ attrs[k] = String(v); }, removeAttribute: function(k){ delete attrs[k]; }, contains: function(){ return false; },
    matches: function(sel){ return /vd-item\[data-dbkey\]/.test(sel); },
    querySelector: function(sel){ return /d2art-wrap/.test(sel) ? art : null; },
    closest: function(sel){ return /vd-item\[data-dbkey\]/.test(sel) ? el : null; },
    getBoundingClientRect: function(){ return { left: 0, top: 0, width: 40, height: 120, right: 40, bottom: 120 }; } };
  return el;
}
var FILED = [];
function door(){ window.vaultFile = function(n, w, o){ FILED.push({ n: n, by: w && w.by, where: w && w.where, mule: o && o.mule });
  assign[n] = o.mule; return { ok: true, mode: 'filed', mule: o.mule }; }; }
var TIP = null;
function spyTip(){ TIP = null; window.d2Tip.show = function(e){ TIP = { name: e && e.name, base: e && e.base }; }; }
"""


def _drive(scenario, assign=None, store=None, builder=True):
    """the shipped mule window (+ the builder's block and the mule tooltip script when `builder`), one node program"""
    s = EQ._src()
    tables = EQ._line(s, "const ITEM_CODEX = {") + EQ._line(s, "const ITEM_TIP = {") + EQ._sets_and_runewords(s)
    helpers = (EQ._line(s, "  var RK='d2r_muleRoster', AK='d2r_muleAssign';")
               + EQ._guard(s) + EQ._line(s, "  function saveR(){ _guardedSet(RK, JSON.stringify(roster)); }")
               + EQ._line(s, "  function art(n, glyph, size){")
               + EQ._line(s, "  function esc(t){ return String(t)")
               + EQ._line(s, "  function jsArg(t){")
               + EQ._between(s, "  function tipOf(n){", "  // RoW shared-stash items never get a mule"))
    extra = (CB._builder_js(s) + "\n" + JN._tip_js(s) + "\n") if builder else ""
    js = _harness() % {
        "store": json.dumps(store or {}), "attrs": json.dumps(_static_attrs()), "db": json.dumps(CB._db_json(s)),
        "assign": json.dumps(assign if assign is not None else {}), "copies": json.dumps({}),
        "tables": tables, "helpers": helpers, "span": _vault_span(), "scenario": extra + MP.HELP + HELP + scenario,
    }
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError("the shipped mule window + picker would not run - UNKNOWN, not passing: %s" % r.stderr[-1500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


_DBC = None


def _db():
    global _DBC
    if _DBC is None:
        _DBC = CB._db()
    return _DBC


def _foot(code):
    b = _db()["b"][code]
    return (b[15], b[16])


def _base_of(item_id):
    if item_id.startswith("b:"):
        return item_id[2:]
    for x in _db()["it"]:
        if x[0] == item_id:
            return x[3]
    raise AssertionError("PRINT THE DENOMINATOR: %s is not in the CB_DB block" % item_id)


#: the kinds an inventory always lists (the builder's CB_MINV_ALWAYS, re-read here from the type codes the data uses)
ALWAYS = {"scha", "mcha", "lcha", "csch", "jewl", "cjwl", "ring", "amul"}
BUILDS = MP.BUILDS
LOCK = MP.AMainLockedItemNeverLandsOnAMule.LOCK.replace("'Harlequin Crest'", "'Annihilus'")


def _ids(*pairs):
    """[(name, quality)] -> their CB_DB ids, each exactly one"""
    out = {}
    for n, q in pairs:
        hit = [x[0] for x in _db()["it"] if x[1] == n and x[2] == q]
        assert len(hit) == 1, "PRINT THE DENOMINATOR: the block holds %d %s items named %s" % (len(hit), q, n)
        out[n] = hit[0]
    return out


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class AnEmptyCellOpensTheDollsPicker(unittest.TestCase):

    def test_every_empty_cell_is_a_control_and_opens_the_mule_host_on_that_cell(self):
        out = _drive("""
          window.openMuleCard('uni-armor');
          out.cells = (invHtml().match(/class="vd-cell"/g) || []).length; out.clickable = clickable(); out.add = /data-add="on"/.test(invHtml());
          out.opened = run(attrOf(cellTag(4, 0), 'onclick'));
          var p = st().pick || {}; out.pick = [p.host, p.kind, p.slot, p.cell, p.tab]; out.tabs = hostTabs();
          out.label = (/id="cb-modal" role="dialog" aria-modal="true" aria-label="([^"]*)"/.exec(box.innerHTML) || [])[1] || null;
          out.on = cellTag(4, 0); out.off = cellTag(5, 0);
          run(attrOf(cellTag(6, 1), 'onkeydown'), { key: 'Enter', preventDefault: function(){} }); out.key = (st().pick || {}).cell;
          out.rail = window._cbRailOf('minv').map(function(r){ return r[0]; });
          out.invRail = window._cbRailOf('inv').map(function(r){ return r[0]; });
          out.invHasRing = window._cbForSlot('inv').some(function(x){ return x[1] === 'The Stone of Jordan'; });""")
        self.assertEqual((out["cells"], out["clickable"], out["add"]), (40, 40, True),
                         "the 10x4 inventory's empty cells are not all controls (GrokBot: 40/40 dead)")
        self.assertIs(out["opened"], True)
        self.assertEqual(out["pick"], ["mule", "inv", "minv", [4, 0], "select"],
                         "an empty cell did not open the builder's picker in the mule host, on that cell, on Select")
        self.assertEqual(out["tabs"], ["Select*", "Edit(off)"], "the inventory's picker is not Select | Edit (no locker tab)")
        self.assertIn("Inventory · col 5 · row 1", out["label"] or "", "the picker does not say which cell it is for")
        self.assertIn('data-on="1"', out["on"] or "", "the cell the picker is open on is not marked")
        self.assertNotIn('data-on="1"', out["off"] or "")
        self.assertEqual(out["key"], [6, 1], "Enter on a cell (its own onkeydown) did not open the picker on it")
        self.assertEqual(out["rail"][0], "Inventory")
        for cat in ("Small Charms", "Large Charms", "Grand Charms", "Crafted Sunder Charms", "Jewels", "Rings", "Amulets",
                    "Helmets", "Body Armor", "Bows"):
            self.assertIn(cat, out["rail"], "the inventory's rail has no %s" % cat)
        self.assertNotIn("Rings", out["invRail"], "a BUILD's inventory rail changed (the mule's list leaked into 'inv')")
        self.assertFalse(out["invHasRing"], "a BUILD's inventory now lists rings")

    def test_the_list_is_what_fits_an_inventory_at_that_cell(self):
        ids = _ids(("Annihilus", "u"), ("Hellfire Torch", "u"), ("Gheed's Fortune", "u"), ("Cold Rupture", "u"),
                   ("The Stone of Jordan", "u"), ("Mara's Kaleidoscope", "u"), ("Harlequin Crest", "u"),
                   ("Windforce", "u"), ("Enigma", "r"))
        out = _drive("""
          var I = %s;
          window.openMuleCard('uni-armor');
          window._mpInvCell(3, 0); out.a = listIds();
          window._mpInvCell(3, 1); out.b = listIds();
          window._mpInvCell(9, 3); out.c = listIds();""" % json.dumps(ids))
        a, b, c = set(out["a"]), set(out["b"]), set(out["c"])
        self.assertGreater(len(a), len(c), "PRINT THE DENOMINATOR: an open cell lists %d, a 1x1 hole %d" % (len(a), len(c)))
        self.assertGreater(len(c), 0, "a 1x1 hole lists nothing")
        for n, i in ids.items():
            self.assertIn(i, a, "an open cell (col 4, row 1) does not list %s" % n)
        for i in ("b:cm1", "b:cm2", "b:cm3", "b:jew"):
            self.assertIn(i, a)
            self.assertIn(i, c, "a charm / jewel base is not always listed (%s missing at a 1x1 hole)" % i)
        self.assertNotIn(ids["Windforce"], b, "a 2x4 bow is offered where only three rows are free")
        self.assertIn(ids["Harlequin Crest"], b)
        for n in ("Harlequin Crest", "Enigma", "Windforce"):
            self.assertNotIn(ids[n], c, "%s is offered for a 1x1 hole" % n)
        for n in ("Annihilus", "Gheed's Fortune", "Cold Rupture", "The Stone of Jordan", "Mara's Kaleidoscope"):
            self.assertIn(ids[n], c, "%s (an inventory kind) is not always listed" % n)
        # THE RULE, row by row: at the 1x1 hole every row is an inventory kind or an item whose base is 1x1
        for i in c:
            base = _base_of(i) if not i.startswith("b:") else i[2:]
            if base.startswith("@"):
                continue
            kind = _db()["b"][base][1]
            self.assertTrue(kind in ALWAYS or _foot(base) == (1, 1),
                            "%s (%s, %dx%d) is listed for a 1x1 hole" % (i, kind, _foot(base)[0], _foot(base)[1]))

    def test_a_covered_cell_opens_nothing_and_no_builder_means_no_clickable_cell(self):
        pos = {MULE: {"The Stone of Jordan": {"tab": "inv", "page": 0, "x": 2, "y": 1, "at": "2026-09-27T00:00:00Z"}}}
        out = _drive("""
          window.openMuleCard('uni-armor'); out.n = clickable(); out.covered = window._mpInvCell(2, 1); out.pick = !!st().pick;""",
                     assign={"The Stone of Jordan": MULE}, store={"d2r_mulePos": json.dumps(pos)})
        self.assertEqual(out["n"], 39, "the cell a locker item sits on is still drawn as an empty control")
        self.assertIs(out["covered"], False, "a covered cell opened the picker")
        self.assertFalse(out["pick"])
        out = _drive("""
          window.openMuleCard('uni-armor'); out.n = clickable(); out.grid = (/<div class="vd-grid"[^>]*data-area="inv"[^>]*>/.exec(invHtml()) || [''])[0];
          out.opened = window._mpInvCell(0, 0);""", builder=False)
        self.assertEqual(out["n"], 0, "with no picker on the page a cell still claims to be clickable")
        self.assertIn('data-add="off"', out["grid"])
        title = (re.search(r' title="([^"]*)"', out["grid"]) or [None, ""])[1]
        self.assertIn("UNKNOWN", title, "the grid's title does not say the database is missing - it reads as an empty inventory")
        self.assertIs(out["opened"], False)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class AGrandCharmLandsWhereHeClicked(unittest.TestCase):

    def test_a_grand_charm_lands_1x3_on_the_clicked_cell_and_never_in_a_build(self):
        out = _drive("""
          var before = STORE['d2r_charBuilds'], beforeSel = STORE['d2r_cbSel'];
          window.openMuleCard('uni-armor');
          out.ok = pickAt(4, 0, 'b:cm3'); out.tab = st().pick && st().pick.tab; out.err = st().hostErr;
          out.store = invList(); out.tiles = dbTiles(); out.n = clickable();
          var ld = window._muleLoad(window._muleNamesFor('uni-armor'), window._mpWornFor('uni-armor', eq()), 'uni-armor');
          out.fault = window._gridFault(ld.mules[0].inv, 10, 4);
          out.builds = STORE['d2r_charBuilds'] === before; out.sel = STORE['d2r_cbSel'] === beforeSel;""",
                     store={"d2r_charBuilds": BUILDS, "d2r_cbSel": "b1"})
        self.assertIs(out["ok"], True, "the grand charm was not placed: %r" % out["err"])
        self.assertEqual(out["tab"], "edit")
        self.assertEqual(len(out["store"]), 1)
        e = out["store"][0]
        self.assertEqual((e["name"], e["page"], e["x"], e["y"], e["w"], e["h"], e["source"], e["id"], e["base"]),
                         ("Grand Charm", 0, 4, 0, 1, 3, "manual", "b:cm3", "cm3"),
                         "the mule's inventory record is not the grand charm, 1x3, at the clicked cell, placed by hand")
        self.assertEqual([(t["n"], t["x"], t["y"], t["w"], t["h"]) for t in out["tiles"]], [("Grand Charm", 4, 0, 1, 3)],
                         "the window does not draw the grand charm on the cells it holds")
        self.assertEqual(out["n"], 37, "the three cells under the grand charm are still drawn as empty controls")
        self.assertFalse(out["fault"]["fault"], "the inventory's grid-fault instrument fired: %r" % out["fault"])
        self.assertTrue(out["builds"], "an inventory pick touched d2r_charBuilds")
        self.assertTrue(out["sel"], "an inventory pick touched d2r_cbSel")

    def test_every_charm_takes_its_size_from_the_one_source(self):
        ids = _ids(("Annihilus", "u"), ("Hellfire Torch", "u"), ("Gheed's Fortune", "u"), ("Cold Rupture", "u"),
                   ("The Stone of Jordan", "u"))
        cells = [("b:cm1", 0, 0), ("b:cm2", 1, 0), ("b:cm3", 2, 0), (ids["Annihilus"], 3, 0), (ids["Hellfire Torch"], 4, 0),
                 (ids["Gheed's Fortune"], 5, 0), (ids["Cold Rupture"], 6, 0), ("b:jew", 7, 0), (ids["The Stone of Jordan"], 8, 0)]
        out = _drive("""
          window.openMuleCard('uni-armor');
          out.ok = %s.map(function(c){ return place(c[1], c[2], c[0]) || st().hostErr; });
          out.store = invList();
          window.openCharBuilder(); window._cbCell(0, 0); out.bok = window._cbChoose('b:cm3');
          var b = JSON.parse(STORE['d2r_charBuilds'] || '{}'), k = Object.keys(b)[0], inv = k ? b[k].sets[0].inv : [];
          out.built = inv.map(function(e){ return [e.name, e.w, e.h]; });""" % json.dumps(cells))
        self.assertEqual(out["ok"], [True] * len(cells), "a charm was refused on an open cell: %r" % out["ok"])
        got = dict(((e["x"], e["y"]), (e["w"], e["h"])) for e in out["store"])
        # D2R's table, as his ask states it - and the builder's one source must say the same for each base
        d2r = {"b:cm1": (1, 1), "b:cm2": (1, 2), "b:cm3": (1, 3), ids["Annihilus"]: (1, 1), ids["Hellfire Torch"]: (1, 2),
               ids["Gheed's Fortune"]: (1, 3), ids["Cold Rupture"]: (1, 3), "b:jew": (1, 1), ids["The Stone of Jordan"]: (1, 1)}
        for i, x, y in cells:
            self.assertEqual(_foot(_base_of(i)), d2r[i], "CB_DB's size for %s is not D2R's" % i)
            self.assertEqual(got.get((x, y)), d2r[i], "%s landed %r, D2R says %r" % (i, got.get((x, y)), d2r[i]))
        self.assertIs(out["bok"], True)
        self.assertEqual(out["built"], [["Grand Charm", 1, 3]], "the builder's own inventory does not read the same size")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class APickThatDoesNotFitIsRefusedWithItsReason(unittest.TestCase):

    def test_off_the_grid_is_refused_and_said(self):
        out = _drive("""
          window.openMuleCard('uni-armor'); window._mpInvCell(4, 3); out.listed = listIds().indexOf('b:cm3') >= 0;
          out.ok = window._cbChoose('b:cm3'); out.err = st().hostErr; out.tab = st().pick.tab;
          out.alert = /cb-host-err/.test(box.innerHTML); out.store = invList();""")
        self.assertTrue(out["listed"], "a grand charm is not listed at row 4 - the refusal cannot be reached from the list")
        self.assertIs(out["ok"], False, "a 1x3 at row 4 was placed off the 10x4 grid")
        self.assertIn("Grand Charm does not fit there", out["err"])
        self.assertIn("runs past the edge of the 10×4 inventory", out["err"])
        self.assertEqual((out["tab"], out["alert"], out["store"]), ("select", True, []),
                         "a refused pick flipped to Edit, was not said, or was stored")

    def test_over_a_database_tile_and_over_a_locker_tile_is_refused(self):
        ids = _ids(("Annihilus", "u"))
        out = _drive("""
          window.openMuleCard('uni-armor'); out.a = pickAt(7, 2, '%s');
          out.ok = pickAt(7, 0, 'b:cm3'); out.err = st().hostErr; out.store = invList().map(function(e){ return e.name; });""" % ids["Annihilus"])
        self.assertIs(out["a"], True)
        self.assertIs(out["ok"], False, "a grand charm was placed over Annihilus")
        self.assertIn("would cover Annihilus (col 8 · row 3)", out["err"])
        self.assertEqual(out["store"], ["Annihilus"])
        pos = {MULE: {"The Stone of Jordan": {"tab": "inv", "page": 0, "x": 2, "y": 1, "at": "2026-09-27T00:00:00Z"}}}
        out = _drive("""
          window.openMuleCard('uni-armor'); out.ok = pickAt(2, 0, 'b:cm3'); out.err = st().hostErr; out.store = invList();""",
                     assign={"The Stone of Jordan": MULE}, store={"d2r_mulePos": json.dumps(pos)})
        self.assertIs(out["ok"], False, "a grand charm was placed over the ring he placed there by hand")
        self.assertIn("would cover The Stone of Jordan", out["err"])
        self.assertEqual(out["store"], [])

    def test_a_replacement_that_does_not_fit_leaves_the_tile(self):
        ids = _ids(("Annihilus", "u"))
        out = _drive("""
          window.openMuleCard('uni-armor'); pickAt(0, 2, '%s'); var k = keyOf('Annihilus'); window._mpInvCell(null);
          window._mpInvTile(k); window._cbPickTab('select'); out.ok = window._cbChoose('b:cm3'); out.err = st().hostErr;
          out.store = invList().map(function(e){ return [e.key === k, e.name, e.x, e.y, e.w, e.h]; });""" % ids["Annihilus"])
        self.assertIs(out["ok"], False, "a 1x3 replaced a 1x1 at row 3 and ran off the grid")
        self.assertIn("runs past the edge", out["err"])
        self.assertEqual(out["store"], [[True, "Annihilus", 0, 2, 1, 1]], "the refused replacement changed the tile")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class AFilledTileShowsTheGameTooltipAndReplacesOrRemoves(unittest.TestCase):

    def test_a_click_opens_edit_and_shows_the_builders_box_over_the_stored_entry(self):
        ids = _ids(("Annihilus", "u"))
        out = _drive("""
          window.openMuleCard('uni-armor'); pickAt(0, 0, '%s'); var k = keyOf('Annihilus'); window._mpInvCell(null);
          out.closed = !st().pick; spyTip();
          out.ok = run(attrOf(tileTag(k), 'onclick')); var p = st().pick || {}; out.pick = [p.kind, p.tab, p.i, p.cell]; out.tabs = hostTabs();
          var m = modalHtml() || ''; out.remove = m.indexOf('✕ Remove') >= 0; out.change = m.indexOf('⟳ Change Item') >= 0;
          out.tip = TIP; out.sel = /class="vd-item vd-db[^"]*vd-db-on"/.test(invHtml());""" % ids["Annihilus"])
        self.assertTrue(out["closed"], "the fixture's picker did not close - this case cannot bite")
        self.assertIs(out["ok"], True)
        self.assertEqual(out["pick"], ["inv", "edit", 0, [0, 0]], "a click on the tile did not open Edit on it")
        self.assertEqual(out["tabs"], ["Select", "Edit*"])
        self.assertTrue(out["remove"] and out["change"], "Edit has no Remove / Change Item")
        self.assertEqual(out["tip"], {"name": "Annihilus", "base": "Small Charm"},
                         "the click did not show the builder's in-game box over the stored entry")
        self.assertTrue(out["sel"], "the tile being edited is not marked")

    def test_a_runeword_waits_on_its_base_tab_and_its_box_is_its_stored_entry(self):
        ids = _ids(("Enigma", "r"), ("Spirit", "r"))
        out = _drive("""
          var I = %s; window.openMuleCard('uni-armor');
          window._mpInvCell(0, 0); out.tab = (window._cbChoose(I.Spirit), st().pick.tab); out.b00 = baseCodes();
          window._mpInvCell(0, 1); window._cbChoose(I.Spirit); out.b01 = baseCodes();
          window._mpInvCell(0, 0); window._cbChoose(I.Enigma); out.enigma = baseCodes();
          out.ok = window._cbPickBase('xtp'); out.store = invList();
          var k = keyOf('Enigma'); out.art = artOf(k);
          window._mpInvCell(null); spyTip(); fire('mouseover', { target: tileEl(k), buttons: 0 }); out.hover = TIP;""" % json.dumps(ids))
        self.assertEqual(out["tab"], "base", "a runeword in the inventory went on its first base (no Base tab)")
        b00, b01 = set(out["b00"]), set(out["b01"])
        self.assertGreater(len(b00), len(b01), "PRINT THE DENOMINATOR: Spirit's bases at row 1: %d, at row 2: %d" % (len(b00), len(b01)))
        self.assertGreater(len(b01), 0)
        for c in b01:
            self.assertLessEqual(_foot(c)[1], 3, "Spirit's Base tab at row 2 offers %s (%dx%d), which does not fit" % ((c,) + _foot(c)))
        self.assertTrue([c for c in b00 - b01 if _foot(c)[1] == 4], "no 4-row base was left out at row 2 - this case cannot bite")
        self.assertIn("xtp", out["enigma"])
        self.assertIs(out["ok"], True)
        e = out["store"][0]
        self.assertEqual((e["name"], e["base"], e["w"], e["h"], e["x"], e["y"]), ("Enigma", "xtp", 2, 3, 0, 0))
        self.assertEqual(out["art"], "Mage Plate", "the fixture's tile does not draw its base - this case cannot bite")
        self.assertEqual(out["hover"], {"name": "Enigma", "base": "Mage Plate"},
                         "the tile's hover re-read the art's name instead of the stored entry")

    def test_replace_keeps_the_cell_and_remove_or_delete_takes_it_off(self):
        ids = _ids(("Annihilus", "u"), ("Hellfire Torch", "u"))
        out = _drive("""
          var I = %s; window.openMuleCard('uni-armor'); pickAt(0, 0, I.Annihilus); var k = keyOf('Annihilus'), at0 = invList()[0].at;
          window._mpInvCell(null); window._mpInvTile(k); window._cbPickTab('select'); out.rep = window._cbChoose(I['Hellfire Torch']);
          out.after = invList().map(function(e){ return [e.key === k, e.name, e.x, e.y, e.w, e.h, e.at !== at0]; });
          window._cbUnequip(); out.removed = invList(); out.tab = st().pick && st().pick.tab; out.n = clickable();
          out.jq = place(5, 1, 'b:jew'); var j = keyOf('Jewel'); out.jewel = invList().map(function(e){ return [e.name, e.q]; }); window._mpInvCell(null);
          out.del = run(attrOf(tileTag(j), 'onkeydown'), { key: 'Delete', preventDefault: function(){} }); out.gone = invList();""" % json.dumps(ids))
        self.assertIs(out["rep"], True)
        self.assertEqual(out["after"], [[True, "Hellfire Torch", 0, 0, 1, 2, True]],
                         "a replacement did not land on the tile's own cell, at its own size, as a new placement")
        self.assertEqual((out["removed"], out["tab"], out["n"]), ([], "select", 40), "Remove did not take the tile off")
        self.assertIs(out["jq"], True)
        self.assertEqual(len(out["jewel"]), 1, "the fixture's jewel was never placed - the Delete case cannot bite")
        self.assertEqual(out["gone"], [], "Delete on a tile did not remove it")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class AMainLockedCharmIsRefused(unittest.TestCase):

    def test_a_locked_charm_is_refused_and_says_who_holds_it(self):
        ids = _ids(("Annihilus", "u"), ("Gheed's Fortune", "u"))
        out = _drive(LOCK + """
          var I = %s; window.openMuleCard('uni-armor');
          out.ok = pickAt(0, 0, I.Annihilus); out.err = st().hostErr; out.eq = STORE['d2r_muleEquip'] || null;
          out.alert = /cb-host-err/.test(box.innerHTML);
          out.ok2 = pickAt(0, 0, I["Gheed's Fortune"]); out.store = invList().map(function(e){ return e.name; });""" % json.dumps(ids))
        self.assertIs(out["ok"], False, "a MAIN-locked charm was placed in a mule's inventory")
        self.assertIn("is locked to your MAIN", out["err"])
        self.assertIn("worn by the MAIN in 3 sessions", out["err"], "the refusal does not say which source holds the lock")
        self.assertIsNone(out["eq"], "a refused pick wrote d2r_muleEquip")
        self.assertTrue(out["alert"], "the refusal is not shown in the picker")
        self.assertIs(out["ok2"], True, "a free charm was refused too")
        self.assertEqual(out["store"], ["Gheed's Fortune"])


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheDoorFilesItOnceAndItIsOneItem(unittest.TestCase):

    def test_a_new_placement_files_through_the_door_and_an_edit_does_not(self):
        ids = _ids(("Annihilus", "u"))
        out = _drive("""
          door(); window.openMuleCard('uni-armor'); out.ok = pickAt(2, 0, '%s'); out.filed = FILED.slice(); var at0 = invList()[0].at;
          window._cbEdit('ilvl', 80); out.after = invList().map(function(e){ return [e.ilvl, e.at === at0]; }); out.filed2 = FILED.length;""" % ids["Annihilus"])
        self.assertIs(out["ok"], True)
        self.assertEqual(out["filed"], [{"n": "Annihilus", "by": "hand", "where": "the mule window (UNI-ARMOR)", "mule": MULE}],
                         "a new inventory placement was not filed to the mule through the door, by his hand")
        self.assertEqual(out["after"], [[80, True]], "Edit did not edit the tile in place (the placement keeps its time)")
        self.assertEqual(out["filed2"], 1, "an edit filed the item a second time")

    def test_two_identical_charms_are_two_copies_and_a_second_mule_does_not_take_the_first(self):
        out = _drive("""
          door();
          window.openMuleCard('uni-armor');
          out.a = pickAt(0, 0, 'b:cm3'); out.a2 = pickAt(1, 0, 'b:cm3');
          out.tilesA = dbTiles().length; out.itemsA = itemsBox(); out.physA = copiesBox(); out.emptyA = /empty locker/.test(box.innerHTML);
          var invA = (eq()['uni-armor'] || {}).inv || {};
          out.keysA = Object.keys(invA); out.copiesA = out.keysA.map(function(k){ return invA[k].copy || null; });
          window.openMuleCard('uni-weap'); out.b = pickAt(0, 0, 'b:cm3');
          out.tilesB = dbTiles().length; out.itemsB = itemsBox(); out.physB = copiesBox();
          window.openMuleCard('uni-armor');
          out.tilesA2 = dbTiles().length; out.itemsA2 = itemsBox(); out.physA2 = copiesBox(); out.emptyA2 = /empty locker/.test(box.innerHTML);
          out.home = assign['Grand Charm'] || null;
          out.filed = FILED.map(function(f){ return f.n; });""")
        self.assertIs(out["a"], True, "the first grand charm was not placed")
        self.assertIs(out["a2"], True, "a second identical grand charm was not placed: the two counted as one")
        self.assertIs(out["b"], True, "the same charm was not placed on a second mule")
        # #76 v3755 — generic grand charms carry no grail NAME (not filed to assign; home is None below), so the
        # headline "Items" (distinct NAMED items = the shelf card's _muleNamesFor count) is 0, while the grid still
        # draws each physical charm as its own tile (2) and physical "Copies" reads 2. Card and locker agree at 0.
        self.assertEqual((out["tilesA"], out["itemsA"], out["physA"]), (2, 0, 2),
                         "two grand charms: %s tile(s), Items(named) %s, Copies(physical) %s"
                         % (out["tilesA"], out["itemsA"], out["physA"]))
        self.assertEqual(len(set(out["keysA"])), 2, "the two copies do not have their own store keys: %r" % out["keysA"])
        self.assertEqual(sorted(out["copiesA"]), sorted(out["keysA"]),
                         "a copy's identity is not its own key: %r" % out["copiesA"])
        self.assertFalse(out["emptyA"], "two placed charms read as an empty locker")
        self.assertEqual((out["tilesB"], out["itemsB"], out["physB"]), (1, 0, 1),
                         "the second mule did not count its own copy")
        self.assertEqual((out["tilesA2"], out["itemsA2"], out["physA2"]), (2, 0, 2),
                         "reopening the first mule lost a copy or stopped counting it")
        self.assertFalse(out["emptyA2"], "the first mule reads empty while its charms are still there")
        self.assertIsNone(out["home"], "a generic charm was filed by name, so the copies are one item: %r" % out["home"])
        self.assertNotIn("Grand Charm", out["filed"],
                         "the name door took a generic charm: %r" % out["filed"])

    def test_the_filed_charm_is_one_item_on_the_grid(self):
        ids = _ids(("Annihilus", "u"))
        out = _drive("""
          door(); window.openMuleCard('uni-armor'); pickAt(2, 0, '%s'); out.assigned = assign['Annihilus'] || null;
          out.placed = allTiles('Annihilus'); window._cbUnequip(); out.removed = allTiles('Annihilus');""" % ids["Annihilus"])
        self.assertEqual(out["assigned"], MULE, "the fixture's door did not file the name - this case cannot bite")
        self.assertEqual(out["placed"], {"tiles": 1, "phys": 1, "worn": 0},
                         "the filed charm is drawn twice - its database tile AND a packed copy of the same name")
        self.assertEqual(out["removed"], {"tiles": 1, "phys": 1, "worn": 0},
                         "after Remove the locker's filed copy is not packed once (it stays filed: Remove is not an unfile)")

    def test_a_doll_pick_the_door_filed_is_worn_not_packed_again(self):
        ids = _ids(("Tyrael's Might", "u"))
        out = _drive("""
          door(); window.openMuleCard('uni-armor'); window._mpPick('tors'); window._cbQt('u');
          out.ok = window._cbChoose('%s'); out.assigned = assign["Tyrael's Might"] || null; out.t = allTiles("Tyrael's Might");
          window._cbPickTab('locker'); out.here = /aria-label="worn here now: Tyrael&#39;s Might"/.test(box.innerHTML);""" % ids["Tyrael's Might"])
        self.assertIs(out["ok"], True)
        self.assertEqual(out["assigned"], MULE, "the fixture's door did not file the doll pick - this case cannot bite")
        self.assertEqual(out["t"], {"tiles": 0, "phys": 1, "worn": 1},
                         "a doll pick the door filed is worn AND packed in the grid (one Tyrael's Might, drawn twice)")
        self.assertTrue(out["here"], "the doll's In this locker tab does not say the filed pick is worn here now")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class EscClosesTheTopLayerThenThePickerThenTheWindow(unittest.TestCase):

    def test_esc_order(self):
        out = _drive("""
          window.openMuleCard('uni-armor'); window._mpInvCell(1, 1); window._cbFiltToggle();
          fire('keydown', { key: 'Escape' }); out.e1 = [st().filtOpen, !!st().pick, !!modalHtml()];
          fire('keydown', { key: 'Escape' }); out.e2 = [!!st().pick, !!modalHtml(), box.hidden];
          fire('keydown', { key: 'Escape' }); out.e3 = box.hidden;""")
        self.assertEqual(out["e1"], [False, True, True], "the first Esc did not close the Filters list alone")
        self.assertEqual(out["e2"], [False, False, False], "the second Esc did not close the inventory's picker (and only it)")
        self.assertIs(out["e3"], True, "the third Esc did not close the window")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class AStoredRecordThatCannotBeLaidIsSaid(unittest.TestCase):
    """the doctor: a record nothing can lay is a conflict with its reason, never drawn, never a guessed size"""

    STORE = {MULE: {"inv": {
        "good": {"name": "Small Charm", "source": "manual", "at": "2026-09-27T00:00:01Z", "page": 0, "x": 0, "y": 0,
                 "w": 1, "h": 1, "id": "b:cm1", "base": "cm1"},
        "off": {"name": "Grand Charm", "source": "manual", "at": "2026-09-27T00:00:02Z", "page": 0, "x": 9, "y": 2,
                "w": 1, "h": 3, "id": "b:cm3", "base": "cm3"},
        "nosize": {"name": "Annihilus", "source": "manual", "at": "2026-09-27T00:00:03Z", "page": 0, "x": 5, "y": 0,
                   "w": None, "h": None}}}}

    def test_a_record_that_cannot_be_laid_is_a_conflict_said_and_removable(self):
        out = _drive("""
          window.openMuleCard('uni-armor');
          var ld = window._muleLoad(window._muleNamesFor('uni-armor'), window._mpWornFor('uni-armor', eq()), 'uni-armor');
          out.bad = ld.conflicts.map(function(c){ return [c.key, c.why]; }).sort(); out.tiles = dbTiles().map(function(t){ return t.n; });
          out.fault = window._gridFault(ld.mules[0].inv, 10, 4).fault;
          var h = box.innerHTML, i = h.indexOf('mp-bad-db'); out.say = i < 0 ? null : unesc(h.slice(i, h.indexOf('</div>', i))).replace(/<[^>]+>/g, '');
          out.row = /Hand-placed spots that no longer fit<\\/td><td>2</.test(h);
          out.rm = window._mpInvRemoveKey('nosize'); out.left = Object.keys(invStore()).sort();""",
                     store={"d2r_muleEquip": json.dumps(self.STORE)})
        self.assertEqual([k for k, _ in out["bad"]], ["db:nosize", "db:off"])
        why = dict(out["bad"])
        self.assertIn("runs past the edge of the 10×4 inventory", why["db:off"])
        self.assertIn("its size is not on record", why["db:nosize"])
        self.assertEqual(out["tiles"], ["Small Charm"], "a record that cannot be laid was drawn anyway")
        self.assertFalse(out["fault"])
        self.assertIsNotNone(out["say"], "the window does not say a database record could not be laid")
        self.assertIn("size UNKNOWN", out["say"], "an unrecorded size was not said as UNKNOWN")
        self.assertIn("not drawn", out["say"])
        self.assertTrue(out["row"], "CALCULATIONS does not count the two spots that no longer fit")
        self.assertIs(out["rm"], True)
        self.assertEqual(out["left"], ["good", "off"], "the banner's remove did not take the record off")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheLoaderNeverAsksTheBuildersDatabase(unittest.TestCase):
    """the shelf card calls _muleLoad for every locker; the builder's 449 KB database is parsed on first open, never at
    boot - so a database tile's art (its base, for a runeword) is asked when the window DRAWS it, never by the loader"""

    def test_the_art_is_asked_when_drawn_not_when_loaded(self):
        store = {MULE: {"inv": {"a": {"name": "Small Charm", "source": "manual", "at": "2026-09-27T00:00:01Z", "page": 0,
                                      "x": 0, "y": 0, "w": 1, "h": 1, "id": "b:cm1", "base": "cm1"}}}}
        out = _drive("""
          var calls = 0, real = window._cbArtName; window._cbArtName = function(e){ calls++; return real(e); };
          var ld = window._muleLoad(window._muleNamesFor('uni-armor'), window._mpWornFor('uni-armor', eq()), 'uni-armor');
          out.loaded = ld.dbPlaced; out.loader = calls; window.openMuleCard('uni-armor'); out.drawn = calls; out.tiles = dbTiles().length;""",
                     store={"d2r_muleEquip": json.dumps(store)})
        self.assertEqual((out["loaded"], out["tiles"]), (1, 1), "the fixture's record was not laid and drawn - this case cannot bite")
        self.assertEqual(out["loader"], 0, "the loader asked the builder's database for a tile's art (the shelf card would parse it)")
        self.assertGreater(out["drawn"], 0, "drawing the tile never asked its art (a runeword would draw its own name)")


RED_PROOF = [
    {
        "why": "2026-09-27 - a generic charm is filed by name, so two Grand Charms are one item and the second mule takes the first",
        "file": "bible.html",
        "find": "            if (_mpIsGenericCopy(e)) return;\n",
        "replace": "            if (false) return;\n",
        "matches": 1,
    },
    {
        "why": "2026-09-27 - two identical charms on the grid count as the one named copy",
        "file": "bible.html",
        "find": "    return { sized: sized, phys: sized.length + _wornN + _db.n, worn: _wornN, cells: cells, mules: mules, rem: rem,\n",
        "replace": "    return { sized: sized, phys: sized.length + _wornN + _dbInLocker, worn: _wornN, cells: cells, mules: mules, rem: rem,\n",
        "matches": 1,
    },
    {
        "why": "2026-09-27 - charms placed from the database read as an empty locker because the name was not filed",
        "file": "bible.html",
        "find": "      +   ((names.length || (_load.dbPlaced | 0) || _spareHtml) ? '' : '<div class=\"vm-empty\" style=\"padding:0 0 8px\">empty locker — assign items on the vault shelf, then this window shows exactly where each one sits</div>')\n",
        "replace": "      +   (names.length ? '' : '<div class=\"vm-empty\" style=\"padding:0 0 8px\">empty locker — assign items on the vault shelf, then this window shows exactly where each one sits</div>')\n",
        "matches": 1,
    },
    {
        "why": "2026-09-27 - a placed charm has no copy of its own, so two identical charms are one record",
        "file": "bible.html",
        "find": "    e.copy = k;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the loader (the shelf card's too) asks the builder's database for a tile's art: a boot-time parse",
        "file": "bible.html",
        "find": "      (out.at[pg] = out.at[pg] || []).push({ n: e.name, dbkey: k,",
        "replace": "      try { window._cbArtName(e); } catch (x) {}\n      (out.at[pg] = out.at[pg] || []).push({ n: e.name, dbkey: k,",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the inventory's cells are dead again (GrokBot: 40/40 did nothing)",
        "file": "bible.html",
        "find": "    if (_add && _add.on){\n",
        "replace": "    if (false){\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the drawn cell's own click and Enter reach nothing (the handler exists, the control is not joined)",
        "file": "bible.html",
        "find": "' onclick=\"window._mpInvCell(' + cx + ',' + cy + ')\" onkeydown=\"window._mpInvCellKey(event,' + cx + ',' + cy + ')\"></div>';",
        "replace": "' onclick=\"void 0\" onkeydown=\"void 0\"></div>';",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the drawn database tile's own click and Delete reach nothing",
        "file": "bible.html",
        "find": "' onclick=\"window._mpInvTile(\\'' + jsArg(p.dbkey) + '\\')\" onkeydown=\"window._mpInvTileKey(event,\\'' + jsArg(p.dbkey) + '\\')\">'",
        "replace": "' onclick=\"void 0\" onkeydown=\"void 0\">'",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - an empty cell's click opens nothing",
        "file": "bible.html",
        "find": "    _mpInvAt = { page: _mulePage, x: x, y: y, key: null };\n",
        "replace": "    return false;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a covered cell opens the picker (a pick there can only be refused)",
        "file": "bible.html",
        "find": "    if (_mpInvFitWhy(_mpInvRects(openMuleId, _mulePage, null, true), x, y, 1, 1)) return false;\n",
        "replace": "    if (false) return false;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the inventory opens a BUILD's inventory list (charms and jewels only: no rings, no Shako)",
        "file": "bible.html",
        "find": "slot: _inv ? CB_MINV : ctx.slot,",
        "replace": "slot: _inv ? 'inv' : ctx.slot,",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the list ignores the free space at the cell (a Shako offered for a 1x1 hole)",
        "file": "bible.html",
        "find": "    if (slot === CB_MINV) rows = rows.filter(_cbMinvOffer());\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the one size source is read crossed (a grand charm lands 3x1)",
        "file": "bible.html",
        "find": "? [b[15] | 0, b[16] | 0] : null;",
        "replace": "? [b[16] | 0, b[15] | 0] : null;",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a pick is placed without the grid rule (off the 10x4, over what is there)",
        "file": "bible.html",
        "find": "    var why = _mpInvFitWhy(rects, spot.x, spot.y, entry.w, entry.h);\n",
        "replace": "    var why = null;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the grid rule is blind to what sits there (a grand charm over Annihilus)",
        "file": "bible.html",
        "find": "      if (x < o.x + ow && o.x < x + w && y < o.y + oh && o.y < y + h)\n",
        "replace": "      if (false)\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the write judges against nothing: the packer's and his hand-placed tiles are not asked",
        "file": "bible.html",
        "find": "rec, at.key, _mpInvRects(openMuleId, at.page, at.key, true));",
        "replace": "rec, at.key, []);",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the inventory's writer stops asking the MAIN lock",
        "file": "bible.html",
        "find": "    var _lkr = _mpLockRefusal(entry);\n    if (_lkr) return { ok: false, all: all, locked: _lkr.locked, why: _lkr.why };\n    var pg = spot && spot.page;\n",
        "replace": "    var pg = spot && spot.page;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - Remove does not take the tile off",
        "file": "bible.html",
        "find": "      r = { ok: true, all: _mpInvRemove(all, openMuleId, at.key), key: null };\n",
        "replace": "      r = { ok: true, all: all, key: null };\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a filled tile's click opens nothing",
        "file": "bible.html",
        "find": "    _mpInvAt = { page: e.page | 0, x: e.x, y: e.y, key: key };\n",
        "replace": "    return false;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a filled tile's click shows no game tooltip",
        "file": "bible.html",
        "find": "      if (el && typeof window._mtShow === 'function') window._mtShow(el);\n",
        "replace": "      if (false) window._mtShow(el);\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a tile's box re-reads the art's name (Enigma on Mage Plate reads as a plain Mage Plate)",
        "file": "bible.html",
        "find": "    if (_ie && _iit && typeof window._cbTipEntry === 'function') entry = window._cbTipEntry(_ie, _iit, null, 'inv');\n",
        "replace": "    if (false) entry = null;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a runeword in the inventory goes on its first base, no Base tab",
        "file": "bible.html",
        "find": "    if (it[2] === 'r' && p.kind === 'inv' && p.slot === CB_MINV){ p.rw = id;",
        "replace": "    if (false){ p.rw = id;",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the Base tab offers bases that do not fit at the cell",
        "file": "bible.html",
        "find": "      if (_fit && !_fit(c)) return false;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - an inventory pick is never written (the host hands the mule its doll slot)",
        "file": "bible.html",
        "find": "(st.pick.kind === 'inv' ? (mb.sets[0].inv || [])[0] : mb.sets[0].slots[st.pick.slot])",
        "replace": "(mb.sets[0].slots[st.pick.slot])",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a filed charm is packed a second time beside its database tile",
        "file": "bible.html",
        "find": "      var _d = Math.min(cc - _w, (_db.hold[n] | 0)); _dbInLocker += _d; _w += _d;",
        "replace": "      var _d = 0;",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - the database's tiles are not laid on the grid (the packer packs over them)",
        "file": "bible.html",
        "find": "      A.inv = (A.inv || []).concat(_db.at[pg]);\n",
        "replace": "      A.inv = (A.inv || []);\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 (the doll sibling) - a doll pick the door filed is worn AND packed in the grid",
        "file": "bible.html",
        "find": "        else if (e.source !== 'import' && e.id && assign[e.name] === muleId) out[e.name] = (out[e.name] || 0) + 1;\n",
        "replace": "        else if (false) out[e.name] = 0;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 (the doll sibling) - the filed doll pick reads 'already worn in another slot' on its own slot",
        "file": "bible.html",
        "find": "_plive.source !== 'import' && (!_plive.id || assign[n] === muleId));",
        "replace": "_plive.source !== 'import' && !_plive.id);",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - Esc no longer closes the inventory's picker (it stays open, or the window goes)",
        "file": "bible.html",
        "find": "    if (!_top) window._mpInvCell(null);\n",
        "replace": "    if (false) window._mpInvCell(null);\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - with no database on the page the grid reads as an empty inventory, not UNKNOWN",
        "file": "bible.html",
        "find": "' data-add=\"off\" title=\"the item database",
        "replace": "' data-add=\"off\" data-x=\"the item database",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a record that cannot be laid is drawn anyway (off the grid, or at a guessed size)",
        "file": "bible.html",
        "find": "      if (why){\n        var _sp = _muleSpotSay('inv',",
        "replace": "      if (false){\n        var _sp = _muleSpotSay('inv',",
        "matches": 1,
    },
    {
        "why": "#174 v-B5 - a database record that cannot be laid is not said on the window",
        "file": "bible.html",
        "find": "      +   ((_load.conflicts || []).filter(function(c){ return c.db; }).length ? (function(cf){ var n = cf.length;\n",
        "replace": "      +   (false ? (function(cf){ var n = cf.length;\n",
        "matches": 1,
    },
]


if __name__ == "__main__":
    if NODE is None:
        sys.stderr.write("⚪ SKIP — node is not on this machine, so the mule inventory was not driven. UNMEASURED, declared (77).\n")
        raise SystemExit(77)
    unittest.main(verbosity=2)
