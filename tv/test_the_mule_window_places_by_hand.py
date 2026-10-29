# -*- coding: utf-8 -*-
"""#174 v-B2 — THE MULE WINDOW PLACES BY HAND: what he drops stays where he dropped it, and the packer flows around it.

His order, 2026-09-25 17:45 (planner/equip/his_mule_locked_21.png — a ring he tried to drag to another box would not
move): "i want them freely being able to be manually overdriven meaning i can move them and unlock them to lock them
in a different cube in the order i choose regardless of where it was vaulted".

THE DEFECT: every item in the mule window was placed by first-fit and nothing else. The tiles had no key, no footprint
and no handler; `_muleLoad` had no notion of a chosen cell, so there was nothing a drag could have written even if one
had started. What this law holds, each case DRIVEN on the SHIPPED vault span of bible.html in node (the packer, the
loader, the window, _mpPlace / _mpUnlock / _mpMoveTo, the board's own tipOf and item tables, the routed store and the
Backup exporter — cut out and run, never re-typed here):

  · THE PACKER TAKES OCCUPANCY. packGrid(items, w, h, occ) never places over a seeded rectangle.
  · A HAND-PLACED ITEM STAYS WHERE IT WAS DROPPED and every other item flows around it: all of them placed once, none
    overlapping, the grid-fault instrument clean — on the first mule and on a spilled second one.
  · A FOOTPRINT THAT DOES NOT FIT IS REFUSED (past the grid's edge, over another item placed by hand, a tab or a mule
    that does not exist) with the reason, and the store is not written. The packer is asked, not the window.
  · A SPOT THAT NO LONGER FITS IS REPORTED, NEVER SILENTLY MOVED: the loader returns it in `conflicts` with why, the
    item is still packed (marked on its tile), the window's NOTES and the shelf card say so, and his spot stays stored.
  · UNLOCK returns it to auto-pack: the spot leaves the store and first-fit places the item again.
  · A MOVE TO ANOTHER MULE (a drop on its tab) and to another STASH TAB lands in the first free cell there, locked.
  · COPIES are placed one by one ("<name> #2").
  · THE STORE (d2r_mulePos) forks per world like d2r_muleAssign and rides Backup & Share.
  · THE SHELF CARD AND THE WINDOW AGREE: the shelf's SHIPPED line calls the same _muleLoad with the locker's id, and
    what it computes is what the window draws. #174 v-B2 fix round: and the SAME NAMES - the MAGIC & RARE locker's
    magicFinds keepers (rolled-name items outside `assign`) were packed by the card and not by the window, so with his
    spots keyed by name the two laid out different items; now both (and the placing code) read _muleNamesFor.
  · ONE COUNT OF A MULE (the Grok seat on v-B, reproduced 2026-09-25: SUMMARY read "On Mule 1: 10 / 19 / 20" as gear
    moved on and off the doll while the line under the stash added up to 20): SUMMARY, CALCULATIONS and the gold box
    print the same total in every state.

  · THE HARNESSES RUN ON THE CI RUNNER. Found while building this: `node -e <cut>` put the whole program in ONE argv
    string, over Linux's 131,072-byte cap — the shell and equip laws were red on CI and green on the Mac. Every
    mule-window harness now hands node its program on stdin, and a case here measures what each would hand the OS.

⚠ WHAT THIS LAW CANNOT SEE: the pointer and the keyboard. That a real press, several moves with the button held and a
release land an item on the cell under the pointer — and survive a reload — is judged in a real browser by
test_the_mule_window_fits_at_every_width.py's drag pass.
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
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
ROOT = os.path.dirname(HERE)
NODE = shutil.which("node")

from test_the_mule_window_is_the_planner_shell import _vault_span, _static_attrs  # noqa: E402  ONE cut
from test_the_mule_window_equips_and_says_its_source import _src, _between, _line, _guard, _sets_and_runewords  # noqa: E402

MULE = "uni-armor"
#: the board's own spellings, with the packer's real footprints (vaultSize answers _itemCells since REG-2051)
SIZES = {"The Stone of Jordan": [1, 1], "Nagelring": [1, 1], "Mara's Kaleidoscope": [1, 1],
         "Harlequin Crest (Shako)": [2, 2], "Magefist": [2, 2], "Arachnid Mesh": [2, 1],
         "Tyrael's Might": [2, 3], "Windforce": [2, 4], "Stormshield": [2, 3]}
LOCKER = sorted(SIZES)


HARNESS = r"""
var STORE = %(store)s, LISTEN = {}, WLISTEN = {}, switched = [], renders = 0;
function mkEl(attrs){
  var cls = {}, a = {};
  Object.keys(attrs || {}).forEach(function(k){ a[k] = attrs[k]; });
  return { hidden: Object.prototype.hasOwnProperty.call(a, 'hidden'), innerHTML: '', scrollTop: 0, parentElement: null,
    classList: { add: function(c){ cls[c] = 1; }, remove: function(c){ delete cls[c]; }, contains: function(c){ return !!cls[c]; } },
    setAttribute: function(k, v){ a[k] = String(v); }, getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(a, k) ? a[k] : null; },
    removeAttribute: function(k){ delete a[k]; }, querySelector: function(){ return null; } };
}
var box = mkEl(%(attrs)s), _html = '';
Object.defineProperty(box, 'innerHTML', { get: function(){ return _html; }, set: function(v){ _html = v; } });
box.querySelector = function(sel){
  if (sel !== '.mp') return null;
  var m = /data-sig="([^"]*)"/.exec(_html);
  return m ? { getAttribute: function(k){ return k === 'data-sig' ? m[1] : null; } } : null;
};
box.contains = function(){ return false; };
var body = { appendChild: function(el){ el.parentElement = body; } };
var document = { body: body, documentElement: mkEl({}), activeElement: null,
  getElementById: function(id){ return id === 'vault-detail' ? box : null; },
  querySelector: function(sel){ return sel === '.tab.active' ? { dataset: { tab: 'vault' } } : null; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(n, f, cap){ (LISTEN[n] = LISTEN[n] || []).push({ f: f, cap: !!cap }); } };
var window = { innerWidth: 2000, innerHeight: 1300, switchTab: function(t){ switched.push(t); },
  addEventListener: function(n, f){ (WLISTEN[n] = WLISTEN[n] || []).push(f); },
  LSR: { getItem: function(k){ return Object.prototype.hasOwnProperty.call(STORE, k) ? STORE[k] : null; },
         setItem: function(k, v){ STORE[k] = String(v); } } };
function setTimeout(f){ f(); } function clearTimeout(){}
var roster = [{ id: 'uni-armor', name: 'UNI-ARMOR', icon: 'A', note: '' }, { id: 'uni-weap', name: 'UNI-WEAPONS', icon: 'W', note: '' }];
function muleById(id){ for (var i = 0; i < roster.length; i++) if (roster[i].id === id) return roster[i]; return null; }
var assign = %(assign)s, COPIES = %(copies)s, SIZES = %(sizes)s;
function vaultSize(n){ return SIZES[n] || [1, 1]; }
function copyCount(n){ return COPIES[n] || 1; }
function artOr(n, g, size){ return '<span class="d2art-wrap ' + (size || 'lg') + '" role="img" aria-label="' + esc(n) + '">' + g + '</span>'; }
function _renderSharedStash(){}
function _itemValue(){ return ''; }
function renderVault(){ renders++; }
%(tables)s
%(helpers)s
%(span)s
function unesc(t){ return String(t).replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&amp;/g, '&'); }
/* every movable tile the window drew: its key, the grid (area + mule) it sits in, its cell and footprint, its marks */
function tiles(){
  var h = box.innerHTML, grids = [], out = [], m;
  var gre = /<div class="vd-grid"[^>]*? data-area="(\w+)" data-page="(\d+)"/g;
  while ((m = gre.exec(h))) grids.push({ area: m[1], page: +m[2], at: m.index });
  var ire = /<div class="vd-item([^"]*)" style="[^"]*" title="([^"]*)" data-key="([^"]*)" data-x="(\d+)" data-y="(\d+)" data-w="(\d+)" data-h="(\d+)"/g;
  while ((m = ire.exec(h))){
    var g = null; grids.forEach(function(p){ if (p.at < m.index) g = p; });
    var end = h.indexOf('</div>', m.index);
    out.push({ key: unesc(m[3]), area: g && g.area, page: g && g.page, x: +m[4], y: +m[5], w: +m[6], h: +m[7],
               held: /\bvd-held\b/.test(m[1]), bad: /\bvd-bad\b/.test(m[1]), title: unesc(m[2]),
               unlock: h.slice(m.index, end).indexOf('class="vd-unlock"') >= 0 });
  }
  return out;
}
function tile(key){ var t = tiles().filter(function(x){ return x.key === key; }); return t.length === 1 ? t[0] : (t.length ? 'TWICE' : null); }
function pos(){ return JSON.parse(STORE['d2r_mulePos'] || '{}'); }
/* the whole load, flattened: [key, mule, area, x, y, w, h, manual, bad] per placed rectangle */
function flat(ld){
  var out = [];
  ld.mules.forEach(function(m, i){
    var areas = { personal: m.stash, inv: m.inv };
    Object.keys(m.tabs || {}).forEach(function(k){ areas[k] = m.tabs[k]; });
    Object.keys(areas).forEach(function(a){ areas[a].forEach(function(p){ out.push([p.key, i, a, p.x, p.y, p.w, p.h, !!p.manual, !!p.bad]); }); });
  });
  return out;
}
function faults(ld){
  var f = [];
  ld.mules.forEach(function(m, i){
    var gs = { personal: [m.stash, 10, 10], inv: [m.inv, 10, 4] };
    Object.keys(m.tabs || {}).forEach(function(k){ gs[k] = [m.tabs[k], 10, 10]; });
    Object.keys(gs).forEach(function(a){ var r = window._gridFault(gs[a][0], gs[a][1], gs[a][2]); if (r.fault) f.push([i, a, r]); });
  });
  return f;
}
function load(){ return window._muleLoad(Object.keys(assign).filter(function(n){ return assign[n] === 'uni-armor'; }).sort(), window._mpWornFor('uni-armor'), 'uni-armor'); }
function counts(){
  var h = box.innerHTML, s = /<span>Copies on Mule (\d+)<\/span><span>(\d+)<\/span>/.exec(h), c = /<td>Copies on Mule \d+<\/td><td>(\d+)<\/td>/.exec(h);
  var g = /<div class="vd-goldbox"(?: title="([^"]*)")?>[^0-9]*(\d+) in stash · (\d+) in inventory · (\d+) (worn|on this mule)<\/div>/.exec(h);
  var gt = g ? (g[5] === 'worn' ? (+g[2] + +g[3] + +g[4]) : +g[4]) : null;
  return { summary: s ? +s[2] : null, calc: c ? +c[1] : null, gold: gt, goldParts: g ? [+g[2], +g[3], +g[4], g[5]] : null };
}
function unescT(t){ return unesc(t); }
function options(){ var re = /data-fk="opt-(\d+)"[^>]*aria-label="(?:equip |worn here now: )([^"]*)"/g, m, out = [];
  while ((m = re.exec(box.innerHTML))) out.push(unesc(m[2])); return out; }
function choose(name){ var o = options(), i = o.indexOf(name); return i < 0 ? 'NOT OFFERED' : window._mpChoose(i); }
var out = {};
%(scenario)s
console.log(JSON.stringify(out));
"""


def _drive(scenario, assign=None, copies=None, store=None, sizes=None):
    s = _src()
    tables = _line(s, "const ITEM_CODEX = {") + _line(s, "const ITEM_TIP = {") + _sets_and_runewords(s)
    helpers = (_line(s, "  var RK='d2r_muleRoster', AK='d2r_muleAssign';")
               + _guard(s) + _line(s, "  function saveR(){ _guardedSet(RK, JSON.stringify(roster)); }")
               + _line(s, "  function art(n, glyph, size){")
               + _line(s, "  function esc(t){ return String(t)")
               + _line(s, "  function jsArg(t){")
               + _between(s, "  function tipOf(n){", "  // RoW shared-stash items never get a mule"))
    js = HARNESS % {
        "store": json.dumps(store or {}), "attrs": json.dumps(_static_attrs()),
        "assign": json.dumps(assign if assign is not None else dict((n, MULE) for n in LOCKER)),
        "copies": json.dumps(copies or {}), "sizes": json.dumps(sizes or SIZES),
        "tables": tables, "helpers": helpers, "span": _vault_span(), "scenario": scenario,
    }
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError("the shipped mule window would not run - UNKNOWN, not passing: %s" % r.stderr[:900])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _no_overlap(testcase, rects, label):
    """rects: flat() rows. Every cell of every grid is claimed at most once, and every key is placed exactly once."""
    seen, cells = {}, {}
    for key, mule, area, x, y, w, h, _m, _b in rects:
        seen[key] = seen.get(key, 0) + 1
        for dx in range(w):
            for dy in range(h):
                c = (mule, area, x + dx, y + dy)
                testcase.assertNotIn(c, cells, "%s: %s and %s both claim %s" % (label, cells.get(c), key, c))
                cells[c] = key
    testcase.assertEqual([k for k, n in seen.items() if n != 1], [], "%s: an item was placed twice" % label)
    return seen


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class ThePackerFlowsAroundWhatHePlaced(unittest.TestCase):

    def test_the_packer_takes_occupancy(self):
        out = _drive("""
          var its = [{n:'A', key:'A', w:2, h:2}, {n:'B', key:'B', w:1, h:1}, {n:'C', key:'C', w:10, h:1}];
          out.free = packGrid(its, 10, 4);
          out.held = packGrid(its, 10, 4, [{x:0, y:0, w:3, h:2}]);""")
        self.assertEqual([(p["n"], p["x"], p["y"]) for p in out["free"]["placed"]], [("A", 0, 0), ("B", 2, 0), ("C", 0, 2)])
        placed = dict((p["n"], (p["x"], p["y"])) for p in out["held"]["placed"])
        self.assertEqual(placed, {"A": (3, 0), "B": (5, 0), "C": (0, 2)}, "first-fit placed over a seeded rectangle")

    def test_a_hand_placed_item_stays_where_dropped_and_the_rest_flow_around_it(self):
        out = _drive("""
          window.openMuleCard('uni-armor');
          out.before = flat(load());
          out.auto = tile('The Stone of Jordan');
          out.r = window._mpPlace('uni-armor', 'The Stone of Jordan', { tab: 'personal', page: 0, x: 0, y: 0 });
          out.pos = pos();
          var ld = load(); out.after = flat(ld); out.faults = faults(ld);
          window.openMuleCard('uni-armor');
          out.tile = tile('The Stone of Jordan'); out.tiles = tiles().length;""")
        self.assertTrue(out["r"]["ok"], out["r"])
        before = dict((r[0], r) for r in out["before"])
        after = dict((r[0], r) for r in out["after"])
        self.assertEqual(before["Windforce"][3:5], [0, 0], "the fixture lost its point: first-fit no longer starts at (0,0)")
        self.assertEqual(after["The Stone of Jordan"][1:8], [0, "personal", 0, 0, 1, 1, True], "the ring is not where he dropped it")
        self.assertNotEqual(after["Windforce"][3:5], [0, 0], "the packer placed Windforce over his ring")
        self.assertEqual(set(after), set(before), "an item went missing or appeared")
        _no_overlap(self, out["after"], "after the drop")
        self.assertEqual(out["faults"], [], "the grid-fault instrument sees an overfull or overlapping grid")
        e = out["pos"][MULE]["The Stone of Jordan"]
        self.assertEqual((e["tab"], e["page"], e["x"], e["y"]), ("personal", 0, 0, 0))
        self.assertRegex(e["at"], r"^\d{4}-\d\d-\d\dT")
        # the window draws what the packer placed: the ring's tile at (0,0), locked, with its unlock
        self.assertFalse(out["auto"]["held"], "an item the packer placed was drawn as placed by hand")
        t = out["tile"]
        self.assertEqual((t["area"], t["page"], t["x"], t["y"], t["w"], t["h"]), ("personal", 0, 0, 0, 1, 1))
        self.assertTrue(t["held"] and t["unlock"], "the ring he placed is not drawn locked with its unlock: %s" % t)
        self.assertIn("placed by hand", t["title"])
        self.assertEqual(out["tiles"], len(LOCKER), "the window does not draw every item as a movable tile")

    def test_a_hand_placed_mule_two_and_the_inventory(self):
        """a big locker spills to Mule 2; his spots on Mule 2 and in the inventory hold, and nothing overlaps"""
        blades = ["Blade %d" % i for i in range(16)]
        a = dict((n, MULE) for n in blades + ["Nagelring"])
        sz = dict((n, [2, 4]) for n in blades)
        sz["Nagelring"] = [1, 1]
        out = _drive("""
          var ld0 = load(); out.mules0 = ld0.mules.length;
          out.r1 = window._mpPlace('uni-armor', 'Nagelring', { tab: 'personal', page: 1, x: 9, y: 9 });
          out.r2 = window._mpPlace('uni-armor', 'Blade 3', { tab: 'inv', page: 0, x: 8, y: 0 });
          var ld = load(); out.after = flat(ld); out.faults = faults(ld); out.mules = ld.mules.length;
          out.occ = [ld.placedCells, ld.lastCells, ld.handPlaced];""", assign=a, sizes=sz)
        self.assertEqual(out["mules0"], 2, "the fixture no longer spills to a second mule")
        self.assertTrue(out["r1"]["ok"] and out["r2"]["ok"], (out["r1"], out["r2"]))
        after = dict((r[0], r) for r in out["after"])
        self.assertEqual(after["Nagelring"][1:5], [1, "personal", 9, 9])
        self.assertEqual(after["Blade 3"][1:5], [0, "inv", 8, 0])
        _no_overlap(self, out["after"], "two mules")
        self.assertEqual(out["faults"], [])
        self.assertEqual(out["occ"][2], 2, "the loader does not count what he placed by hand")
        self.assertEqual(out["occ"][0], 16 * 8 + 1, "the v2212 occupancy (from the placed rectangles) left out the hand-placed ones")

    def test_copies_are_placed_one_by_one(self):
        out = _drive("""
          out.keys = load().sized.filter(function(s){ return s.n === 'Nagelring'; }).map(function(s){ return s.key; });
          out.r = window._mpPlace('uni-armor', 'Nagelring #2', { tab: 'personal', page: 0, x: 9, y: 0 });
          var f = flat(load()).filter(function(r){ return r[0].indexOf('Nagelring') === 0; });
          out.f = f;""", copies={"Nagelring": 2})
        self.assertEqual(out["keys"], ["Nagelring", "Nagelring #2"])
        self.assertTrue(out["r"]["ok"], out["r"])
        rows = dict((r[0], r) for r in out["f"])
        self.assertEqual(rows["Nagelring #2"][3:5] + [rows["Nagelring #2"][7]], [9, 0, True])
        self.assertFalse(rows["Nagelring"][7], "placing one copy locked the other")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class ARefusalAndAReport(unittest.TestCase):

    def test_a_footprint_that_does_not_fit_is_refused_and_nothing_is_written(self):
        out = _drive("""
          out.edge = window._mpPlace('uni-armor', "Tyrael's Might", { tab: 'personal', page: 0, x: 9, y: 0 });
          out.inv = window._mpPlace('uni-armor', "Tyrael's Might", { tab: 'inv', page: 0, x: 0, y: 2 });
          out.store0 = STORE['d2r_mulePos'] || null;
          out.ok = window._mpPlace('uni-armor', 'Magefist', { tab: 'personal', page: 0, x: 4, y: 4 });
          var s1 = STORE['d2r_mulePos'];
          out.over = window._mpPlace('uni-armor', "Tyrael's Might", { tab: 'personal', page: 0, x: 3, y: 3 });
          out.same = STORE['d2r_mulePos'] === s1;
          out.tab = window._mpPlace('uni-armor', 'Nagelring', { tab: 'belt', page: 0, x: 0, y: 0 });
          out.page = window._mpPlace('uni-armor', 'Nagelring', { tab: 'personal', page: 3, x: 0, y: 0 });
          out.half = window._mpPlace('uni-armor', 'Nagelring', { tab: 'personal', page: 0, x: 1.5, y: 0 });
          out.nope = window._mpPlace('uni-armor', 'Not Here', { tab: 'personal', page: 0, x: 0, y: 0 });
          out.shared = window._mpPlace('shared', 'Nagelring', { tab: 'personal', page: 0, x: 0, y: 0 });
          out.final = pos();""")
        self.assertFalse(out["edge"]["ok"])
        self.assertIn("does not fit at col 10", out["edge"]["why"])
        self.assertIn("run past the edge of the 10×10 Personal grid", out["edge"]["why"])
        self.assertFalse(out["inv"]["ok"], "a 2x3 armor was accepted at row 3 of a 4-row inventory")
        self.assertIsNone(out["store0"], "a refused drop wrote the store")
        self.assertTrue(out["ok"]["ok"])
        self.assertFalse(out["over"]["ok"], "an armor was dropped over a glove he placed by hand")
        self.assertIn("Magefist, placed there by hand first", out["over"]["why"])
        self.assertTrue(out["same"], "a refused drop changed the store")
        for k in ("tab", "page", "half", "nope", "shared"):
            self.assertFalse(out[k]["ok"], "%s was accepted: %s" % (k, out[k]))
        self.assertEqual(list(out["final"][MULE]), ["Magefist"])

    def test_a_spot_that_no_longer_fits_is_reported_never_silently_moved(self):
        store = {"d2r_mulePos": json.dumps({MULE: {
            "Magefist": {"tab": "personal", "page": 0, "x": 4, "y": 4, "at": "2026-09-25T10:00:00.000Z"},
            "Harlequin Crest (Shako)": {"tab": "personal", "page": 0, "x": 5, "y": 5, "at": "2026-09-25T11:00:00.000Z"},
            "Tyrael's Might": {"tab": "inv", "page": 0, "x": 9, "y": 0, "at": "2026-09-25T09:00:00.000Z"},
            "Nagelring": {"tab": "belt", "page": 0, "x": 0, "y": 0, "at": "2026-09-25T09:30:00.000Z"}}})}
        out = _drive("""
          var ld = load(); out.conf = ld.conflicts; out.after = flat(ld); out.faults = faults(ld);
          window.openMuleCard('uni-armor');
          out.shako = tile('Harlequin Crest (Shako)'); out.glove = tile('Magefist');
          var h = box.innerHTML, i = h.indexOf('mp-bad-spots'); out.note = i < 0 ? null : unesc(h.slice(i, h.indexOf('</div>', i))).replace(/<[^>]+>/g, '');
          out.calc = /<td>Hand-placed spots that no longer fit<\\/td><td>(\\d+)<\\/td>/.exec(h);
          out.store = STORE['d2r_mulePos'];""", store=store)
        why = dict((c["key"], c["why"]) for c in out["conf"])
        self.assertEqual(sorted(why), sorted(["Harlequin Crest (Shako)", "Tyrael's Might", "Nagelring"]),
                         "the loader did not report exactly the three spots that no longer fit")
        self.assertIn("taken by Magefist, placed there by hand first", why["Harlequin Crest (Shako)"])
        self.assertIn("runs past the edge of the 10×4 Inventory grid", why["Tyrael's Might"])
        self.assertIn('"belt"', why["Nagelring"])
        after = dict((r[0], r) for r in out["after"])
        self.assertEqual(set(after), set(LOCKER), "an item whose spot no longer fits went missing")
        self.assertTrue(after["Harlequin Crest (Shako)"][8], "the item packed in its stead is not marked")
        self.assertEqual(after["Magefist"][3:5] + [after["Magefist"][7]], [4, 4, True], "the older placement lost its spot")
        _no_overlap(self, out["after"], "with conflicts")
        self.assertEqual(out["faults"], [])
        self.assertTrue(out["shako"]["bad"] and out["shako"]["unlock"], out["shako"])
        self.assertIn("no longer fits", out["shako"]["title"])
        self.assertIn("3 items you placed by hand no longer fit their spot", out["note"] or "")
        self.assertIn("Harlequin Crest (Shako) (2×2, wanted Mule 1 · Personal stash · col 6 · row 6)", out["note"] or "")   # REG-3062 the one spelling
        self.assertEqual(out["calc"] and out["calc"][1], "3")
        self.assertEqual(out["store"], store["d2r_mulePos"], "his spots were rewritten — they must be kept until he acts")

    def test_the_shelf_card_reports_it_too(self):
        s = _src()
        blk = _between(s, "        /* #174 v-B2 — the same report the window prints, from the same packer: a spot he chose that no longer fits */",
                       "        + (m.note?'<div class=\"vm-note\">'+esc(m.note)+'</div>':'')")
        js = ("function esc(t){ return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\"/g,'&quot;'); }"
              "var _known = true, _ld = { conflicts: [{ n: 'Shako', spot: 'Personal · Mule 1 · col 6 · row 6', why: 'its cells are taken' }] };"
              "var html = ''\n" + blk + ";\nconsole.log(JSON.stringify(html));")
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr[:400])
        html = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertIn("1 item you placed by hand no longer fits its spot", html)
        self.assertIn("Shako — wanted Personal · Mule 1 · col 6 · row 6: its cells are taken", html)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class UnlockAndMove(unittest.TestCase):

    def test_unlock_returns_it_to_auto_pack(self):
        out = _drive("""
          out.first = flat(load()).filter(function(r){ return r[0] === 'Nagelring'; })[0];
          out.r = window._mpPlace('uni-armor', 'Nagelring', { tab: 'personal', page: 0, x: 9, y: 9 });
          out.placed = flat(load()).filter(function(r){ return r[0] === 'Nagelring'; })[0];
          out.u = window._mpUnlock('uni-armor', 'Nagelring');
          out.again = flat(load()).filter(function(r){ return r[0] === 'Nagelring'; })[0];
          out.store = pos();
          out.u2 = window._mpUnlock('uni-armor', 'Nagelring');""")
        self.assertTrue(out["r"]["ok"] and out["u"]["ok"])
        self.assertEqual(out["placed"][3:5] + [out["placed"][7]], [9, 9, True])
        self.assertEqual(out["again"], out["first"], "unlocked, the ring did not go back to where first-fit puts it")
        self.assertEqual(out["store"], {}, "the unlock left his spot (or an empty locker entry) in the store")
        self.assertFalse(out["u2"]["ok"], "unlocking an item that is not placed by hand claimed to do something")

    def test_a_move_to_another_mule_and_to_another_stash_tab(self):
        blades = ["Blade %d" % i for i in range(16)]
        a = dict((n, MULE) for n in blades + ["Nagelring", "Mara's Kaleidoscope"])
        sz = dict((n, [2, 4]) for n in blades)
        sz["Nagelring"] = [1, 1]
        sz["Mara's Kaleidoscope"] = [1, 1]
        out = _drive("""
          out.was = flat(load()).filter(function(r){ return r[0] === 'Nagelring'; })[0];
          out.m = window._mpMoveTo('uni-armor', 'Nagelring', 1, null);
          out.t = window._mpMoveTo('uni-armor', "Mara's Kaleidoscope", 0, 'gems');
          out.none = window._mpMoveTo('uni-armor', 'Nagelring', 5, null);
          var ld = load(); out.after = flat(ld); out.faults = faults(ld);
          window.openMuleCard('uni-armor'); window._mpSet('stab', 'gems');
          out.gemTile = tile("Mara's Kaleidoscope");
          out.gemTab = /data-tab="gems"[^>]*>Gems <b>(\\d+)<\\/b><\\/button>/.exec(box.innerHTML);""", assign=a, sizes=sz)
        self.assertEqual(out["was"][1], 0, "the fixture's ring does not start on Mule 1")
        self.assertTrue(out["m"]["ok"], out["m"])
        after = dict((r[0], r) for r in out["after"])
        self.assertEqual(after["Nagelring"][1], 1, "a drop on the Mule 2 tab did not move the ring to Mule 2")
        self.assertTrue(after["Nagelring"][7], "the moved ring is not locked there")
        self.assertEqual(out["m"]["spot"]["page"], 1)
        self.assertTrue(out["t"]["ok"], out["t"])
        self.assertEqual(after["Mara's Kaleidoscope"][1:5], [0, "gems", 0, 0], "a drop on the Gems tab did not land in its first cell")
        self.assertFalse(out["none"]["ok"], "a move to a mule the locker does not have was accepted")
        _no_overlap(self, out["after"], "after the moves")
        self.assertEqual(out["faults"], [])
        g = out["gemTile"]
        self.assertEqual((g["area"], g["x"], g["y"], g["held"]), ("gems", 0, 0, True), "the Gems tab does not draw its item")
        self.assertEqual(out["gemTab"] and out["gemTab"][1], "1", "the Gems tab does not say it holds one item")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class OnePackerOneCount(unittest.TestCase):

    def test_the_shelf_card_and_the_window_read_the_same_packer(self):
        s = _src()
        shelf = (_line(s, "      try { if (_isMule && typeof _muleLoad === 'function') _ld = _muleLoad(_muleNamesFor(m.id)")
                 + _line(s, "      catch(e){ _ld = null; }"))
        out = _drive("""
          window._mpPlace('uni-armor', 'The Stone of Jordan', { tab: 'personal', page: 0, x: 9, y: 9 });
          var _isMule = true, items = Object.keys(assign).filter(function(n){ return assign[n] === 'uni-armor'; }).sort(),
              magicItems = [], m = { id: 'uni-armor' }, _ld = null;
          %s
          out.shelf = flat(_ld); out.shelfPct = _ld.lastPct; out.shelfMules = _ld.mules.length;
          window.openMuleCard('uni-armor');
          out.window = tiles().map(function(t){ return [t.key, t.page, t.area, t.x, t.y, t.w, t.h, t.held, t.bad]; });
          out.windowPct = /<span>Last mule’s grid<\\/span><span>(\\d+)%%<\\/span>/.exec(box.innerHTML)[1];
          out.windowMules = /<span>Mules<\\/span><span>(\\d+)<\\/span>/.exec(box.innerHTML)[1];""" % shelf)
        shelf_rows = sorted(out["shelf"])
        self.assertEqual(sorted(out["window"]), shelf_rows, "the window draws a different packing from the shelf card's")
        ring = [r for r in shelf_rows if r[0] == "The Stone of Jordan"][0]
        self.assertEqual(ring[3:5] + [ring[7]], [9, 9, True], "the shelf card's packer does not know his spot")
        self.assertEqual((str(out["shelfPct"]), str(out["shelfMules"])), (out["windowPct"], out["windowMules"]))

    def test_the_magic_and_rare_locker_packs_its_keepers_on_both_surfaces(self):
        """#174 v-B2 fix round - the card packed items + magicFinds, the window packed items only"""
        s = _src()
        shelf = (_line(s, "      try { if (_isMule && typeof _muleLoad === 'function') _ld = _muleLoad(_muleNamesFor(m.id)")
                 + _line(s, "      catch(e){ _ld = null; }"))
        out = _drive("""
          roster.push({ id: 'magic-rare', name: 'MAGIC & RARE', icon: 'M', note: '' });
          var magicFinds = { 'Grim Eye of the Whale': { q: 'rare', base: 'Ring' }, 'Stormeye Coronet': { q: 'magic', base: '' } };
          assign['Nagelring'] = 'magic-rare';
          out.placed = window._mpPlace('magic-rare', 'Grim Eye of the Whale', { tab: 'personal', page: 0, x: 5, y: 5 });
          var _isMule = true, m = { id: 'magic-rare' }, _ld = null;
          %s
          out.shelf = flat(_ld).map(function(r){ return [r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]]; });
          window.openMuleCard('magic-rare');
          out.window = tiles().map(function(t){ return [t.key, t.page, t.area, t.x, t.y, t.w, t.h, t.held, t.bad]; });""" % shelf)
        self.assertTrue(out["placed"]["ok"], "a magicFinds keeper cannot be placed by hand in its own locker: %s" % out["placed"])
        keys = sorted(r[0] for r in out["shelf"])
        self.assertEqual(keys, ["Grim Eye of the Whale", "Nagelring", "Stormeye Coronet"], "PRINT THE DENOMINATOR: %s" % keys)
        self.assertEqual(sorted(out["window"]), sorted(out["shelf"]), "the window lays out different items from the shelf card")
        grim = [r for r in out["window"] if r[0] == "Grim Eye of the Whale"][0]
        self.assertEqual(grim[3:5] + [grim[7]], [5, 5, True], "the keeper he placed is not where he dropped it")

    def test_summary_calculations_and_the_gold_box_count_one_mule_the_same(self):
        """the Grok seat on v-B: SUMMARY 'On Mule 1' read 10 / 19 / 20 as gear moved while the gold box summed to 20"""
        out = _drive("""
          window.openMuleCard('uni-armor'); out.none = counts();
          window._mpPick('head'); out.c1 = choose('Harlequin Crest (Shako)'); out.one = counts();
          window._mpPick('glov'); out.c2 = choose('Magefist');
          window._mpPick('lrin'); out.c3 = choose('Nagelring'); out.three = counts();
          window._mpPlace('uni-armor', "Mara's Kaleidoscope", { tab: 'gems', page: 0, x: 0, y: 0 });
          window.openMuleCard('uni-armor'); out.tab = counts();""")
        self.assertEqual([out["c1"], out["c2"], out["c3"]], [True, True, True], "the fixture could not equip")
        n = len(LOCKER)
        for state in ("none", "one", "three", "tab"):
            c = out[state]
            self.assertEqual((c["summary"], c["calc"], c["gold"]), (n, n, n),
                             "%s: SUMMARY / CALCULATIONS / the line under the stash disagree about one mule: %s" % (state, c))
        self.assertEqual(out["three"]["goldParts"][2:], [3, "worn"])
        self.assertEqual(out["tab"]["goldParts"][0] + out["tab"]["goldParts"][1] + out["tab"]["goldParts"][2], n,
                         "an item in the Gems tab fell out of 'in stash'")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheStoreIsAccountStateAndTravels(unittest.TestCase):

    def _run(self, scenario):
        s = _src()
        router = _between(s, "window._LP_FORKED = new Set([", "// v1478 — THE ROUTE, PUBLISHED.")
        backup = _between(s, "function _collectProgress(){", "function _progressSnapshot(){")
        js = r"""
          var RAWD = {}, RAW = { getItem: function(k){ return Object.prototype.hasOwnProperty.call(RAWD, k) ? RAWD[k] : null; },
            setItem: function(k, v){ RAWD[k] = String(v); }, removeItem: function(k){ delete RAWD[k]; },
            key: function(i){ return Object.keys(RAWD)[i]; } };
          Object.defineProperty(RAW, 'length', { get: function(){ return Object.keys(RAWD).length; } });
          var window = { localStorage: RAW, D2R_PROFILE: 'main' };
          %s
          %s
          var out = {};
          %s
          console.log(JSON.stringify(out));""" % (router, backup, scenario)
        r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("the shipped router / exporter would not run - UNKNOWN: %s" % r.stderr[:600])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_store_forks_per_world_like_the_assignments(self):
        out = self._run("""
          window._D2R_OWNER = false; window._D2R_PFX = 'I·abcd1234·'; window._D2R_LPFX = 'IL·abcd1234·';
          out.guest = [window.LSR.key('d2r_mulePos'), window.LSR.key('d2r_muleAssign')];
          window._D2R_OWNER = true; window._D2R_LPFX = 'L·'; window.D2R_PROFILE = 'ladder';
          out.ladder = [window.LSR.key('d2r_mulePos'), window.LSR.key('d2r_muleAssign')];""")
        self.assertEqual(out["guest"], ["I·abcd1234·d2r_mulePos", "I·abcd1234·d2r_muleAssign"],
                         "a guest's hand-placed spots would land in the owner's store")
        self.assertEqual(out["ladder"], ["L·d2r_mulePos", "L·d2r_muleAssign"], "ladder and main share one set of spots")

    def test_the_store_rides_backup_and_share(self):
        out = self._run("""
          window._D2R_OWNER = false; window._D2R_PFX = 'I·abcd1234·'; window._D2R_LPFX = 'IL·abcd1234·';
          window.LSR.setItem('d2r_mulePos', '{"uni-armor":{"Shako":{"tab":"personal","page":0,"x":3,"y":2,"at":"x"}}}');
          out.snap = _collectProgress();""")
        self.assertEqual(out["snap"].get("d2r_mulePos"), '{"uni-armor":{"Shako":{"tab":"personal","page":0,"x":3,"y":2,"at":"x"}}}',
                         "Backup & Share does not carry his hand-placed spots, so a restore packs every locker from scratch")


class TheHarnessRunsOnTheCIRunner(unittest.TestCase):
    """#174 v-B2 — FOUND WHILE BUILDING THIS LAW: the mule-window laws were RED ON CI and green on his Mac.

    They handed node the whole cut of bible.html as ONE argv string (`node -e <js>`). Linux caps a single argument
    at 131,072 bytes (MAX_ARG_STRLEN); macOS does not. Measured: main 1e1f946e, CI run 36163221309 —
    test_the_mule_window_is_the_planner_shell "FAILED (errors=19)" and ..._equips_and_says_its_source "FAILED
    (errors=26)", each in under 3 s, while both were green here; the vault span alone was 128,195 bytes at that
    commit, the equip law's program ~450 KB. The host machine is a fixture. [[regression-guard]]

    DRIVEN, not read: each law's own _drive runs with subprocess.run captured, and every argv string it would hand
    the OS is measured — the program must travel on stdin and no argument may approach the cap."""

    CAP = 131072

    def _captured(self, call):
        import subprocess as _sp
        from unittest import mock
        seen = []

        class _R(object):
            returncode, stdout, stderr = 0, "{}\n", ""

        def fake(args, **kw):
            seen.append((list(args), len(kw.get("input") or "")))
            return _R()
        with mock.patch.object(_sp, "run", fake):
            call()
        return seen

    def test_every_mule_window_harness_hands_node_its_program_on_stdin(self):
        import test_the_mule_window_is_the_planner_shell as S
        import test_the_mule_window_equips_and_says_its_source as E
        calls = {"planner_shell": lambda: S._drive(),
                 "equips": lambda: E._drive("out.x = 1;"),
                 "places_by_hand": lambda: _drive("out.x = 1;")}
        for name, call in sorted(calls.items()):
            seen = self._captured(call)
            self.assertEqual(len(seen), 1, "%s: its harness did not reach node exactly once" % name)
            args, stdin = seen[0]
            biggest = max(len(a.encode("utf-8")) for a in args)
            self.assertLess(biggest, 4096, "%s hands node a %d-byte argument - Linux refuses anything over %d, so "
                                           "the law cannot start on the CI runner" % (name, biggest, self.CAP))
            self.assertGreater(stdin, 100000, "%s: the program is not on stdin (%d bytes there)" % (name, stdin))


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#174 v-B2 fix round - the window packs the MAGIC & RARE locker without its magicFinds keepers again",
        "file": "bible.html",
        "find": "    var names = _muleNamesFor(muleId);   // #174 v-B2 fix round — the shelf card's list, magicFinds keepers included\n",
        "replace": "    var names = Object.keys(assign).filter(function(n){return assign[n]===muleId;}).sort();\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 fix round - a magicFinds keeper cannot be placed by hand (the placing code lists assign only)",
        "file": "bible.html",
        "find": "    var nm = _muleNamesFor(muleId);   // the window's list: a magicFinds keeper in MAGIC & RARE can be placed by hand too\n",
        "replace": "    var nm = Object.keys(assign).filter(function(n){ return assign[n] === muleId; }).sort();\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - packGrid ignores the occupied rectangles, so first-fit places items over what he placed by hand",
        "file": "bible.html",
        "find": "        for (var ox = Math.max(0, r.x|0); ox < Math.min(gw, (r.x|0) + (r.w||1)); ox++) grid[oy][ox] = true;\n",
        "replace": "        for (var ox = Math.max(0, r.x|0); ox < Math.min(gw, (r.x|0) + (r.w||1)); ox++) void 0;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the loader forgets his spots, so a dropped item snaps back to first-fit (his_mule_locked_21)",
        "file": "bible.html",
        "find": "    var _pos = (muleId != null) ? ((posAll || _mulePosAll())[muleId] || {}) : {};\n",
        "replace": "    var _pos = {};\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - a drop over another hand-placed item is written anyway (the packer is not asked before the store is)",
        "file": "bible.html",
        "find": "    if (bad) return { ok: false, why: 'a ' + it.w + '×' + it.h + ' does not fit there — ' + bad.why };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - a spot that no longer fits is silently moved: nothing reports it",
        "file": "bible.html",
        "find": "        _bad.push({ key: it.key, n: it.n, w: it.w, h: it.h, want: p, spot: _sp, why: why });\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - unlock leaves his spot in the store, so the item never returns to auto-pack",
        "file": "bible.html",
        "find": "    delete all[muleId][key];\n    if (!Object.keys(all[muleId]).length) delete all[muleId];\n",
        "replace": "    if (!Object.keys(all[muleId]).length) delete all[muleId];\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - a drop on another mule's tab lands on the mule it came from",
        "file": "bible.html",
        "find": "        var r = window._mpPlace(muleId, key, { tab: areas[ai], page: page, x: x, y: y });\n",
        "replace": "        var r = window._mpPlace(muleId, key, { tab: areas[ai], page: 0, x: x, y: y });\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - d2r_mulePos stops forking per world, so a guest's spots land in the owner's store",
        "file": "bible.html",
        "find": "\"d2r_muleAssign\", \"d2r_mulePos\", \"d2r_muleRoster\"",
        "replace": "\"d2r_muleAssign\", \"d2r_muleRoster\"",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the shelf card packs without the locker's spots, so the card and the window disagree",
        "file": "bible.html",
        "find": "(typeof _mpWornFor === 'function') ? _mpWornFor(m.id) : null, m.id); }",
        "replace": "(typeof _mpWornFor === 'function') ? _mpWornFor(m.id) : null); }",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - SUMMARY counts the grid only again, so 'On Mule 1' disagrees with the line under the stash when gear is worn",
        "file": "bible.html",
        "find": "    var _onMuleN = _thisMuleN + _wornHere;\n",
        "replace": "    var _onMuleN = _thisMuleN;\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the planner-shell law hands node its 160 KB program as ONE argv string again (Linux caps it at 128 KB: red on CI, green on the Mac)",
        "file": "test_the_mule_window_is_the_planner_shell.py",
        "find": "    r = subprocess.run([NODE, \"-\"], input=js, capture_output=True, text=True, timeout=60)\n",
        "replace": "    r = subprocess.run([NODE, \"-e\", js], capture_output=True, text=True, timeout=60)\n",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - an item in the Shared / Gems / Materials / Runes tabs falls out of what a mule holds",
        "file": "bible.html",
        "find": "      Object.keys(m.tabs || {}).forEach(function(k){ t += m.tabs[k].length; });\n",
        "replace": "",
        "matches": 1,
    },
]
