# -*- coding: utf-8 -*-
"""#174 v-A — THE MULE WINDOW IS THE D2PLANNER BUILDER'S SHELL, AT THEIR MEASURED GEOMETRY, AND IT IS A DIALOG.

His words, 2026-09-25: click a mule and a fullscreen window floats over the vault, with the d2planner's EXACT
layout, structure, UI and UX, in OUR theme, over OUR data; Esc goes back to the vault. Their builder was measured
at 2000px wide (DPR 1): a 1350px content column of three columns, LEFT 322 · CENTRE 716 · RIGHT 300, 6px gutters,
and a paper-doll whose ten slots sit at fixed pixel rects on a 30px cell inside a 322x400 EQUIPMENT panel, with the
10x4 inventory under the doll in the same panel.

Two defects this pins, one of each kind:

  · STRUCTURE. The old card was a two-panel in-game replica (stash | inventory+doll) with a doll on a 10x6 grid
    whose slot shapes matched nothing measured. The shell must carry THEIR slot rects exactly — so this law keeps
    its OWN copy of the measured table (the witness) and compares it with what the SHIPPED openMuleCard renders,
    never with the table the page reads (that would compare the code with itself).
  · ESC SENT HIM HOME. The console forwards Esc into the board only for an overlay it recognises —
    `[role="dialog"]:not([hidden])` among its selectors. #vault-detail matched none, so with the console focused
    Esc closed the SHELL and left the mule window up behind it. The window now declares itself a dialog, from the
    markup AND from openMuleCard, and the console's probe still lists that selector (the other end of the join).

And the honesty rule: a locker has no class, no level and nothing equipped, so every stat is UNKNOWN with a reason
— never a 0, which would read as "measured, and zero". [[unknown-stays-unknown]]

  · DRIVEN (node): the SHIPPED vault span — packer, grid, loader, openMuleCard, close, the Esc listener — is cut
    out of bible.html and run over a minimal DOM stub; every assertion reads what it rendered.
  · READ (source): the CSS column widths and panel heights, the static markup's dialog role, and the console's
    Esc probe selector — each anchored on a string that occurs exactly once.

⚠ WHAT THIS LAW CANNOT SEE, AND WHO DOES. It reads the HTML the window writes, so a sentence that is on the page
but cut in half by its panel passes here — which is exactly how the MERCENARY note lost its "(v-C)" line at 1120
while every case below stayed green. The fit is judged in a real browser by
test_the_mule_window_fits_at_every_width.py. What this law keeps is the STRUCTURE those fixes rest on: the prose
panels are min-height floors, every size in the window rides the unit (--fs-mp-* = token x --kf, floored at
--fs-micro), a header's title and control own grid columns, and a resize re-lays the window only when a layout
number moved (a phone keyboard is a height-only resize, and a re-render replaced the box he was typing in).

⚠ #174 v-B MOVED THREE OF THESE NUMBERS AND #174 v-B2 PUT THEM BACK — THE WITNESS NEVER MOVED. v-B ran the EQUIPMENT
body on its own unit, --du = 1.25 x --u (spec §5's "upgrade"), which widened LEFT to 402 and narrowed the centre to
636. His later word is "literally the same", so DOLL_K is 1: the slots are THEIR_SLOTS on their cell, LEFT is their
322, the centre their 716, the EQUIPMENT panel their 36px header + 364px body. --du stays the doll's unit (the CSS and
the script's MP_DOLL_K are held equal here), and stacked (under 900) it is --u as before.

#174 v-B2 ALSO: the five stash tabs are CONTROLS now (a button per tab, the open one marked, each switching the grid)
— v-B drew them as dim labels with nothing behind them; and the unit also answers the window's HEIGHT (the part he
packs from — header, mule bar, stash panel — fits the viewport, floored at 0.7), so a height-only resize at 1280
re-lays the window exactly when that moves the unit, and never otherwise.
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
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

NODE = shutil.which("node")

# ── THE WITNESS: their builder, measured at 2000x1300, DPR 1 (spec #174 §1). Slot rects relative to the
#    322x400 EQUIPMENT panel: x, y, w, h. This table is deliberately NOT read from the page. ──
THEIR_SLOTS = {
    "rarm": (16, 65, 60, 120),   # right weapon
    "larm": (247, 65, 60, 120),  # left weapon / shield
    "head": (131, 50, 60, 60),
    "neck": (203, 102, 30, 30),  # amulet
    "tors": (131, 125, 60, 90),  # body armor
    "glov": (15, 199, 60, 60),
    "rrin": (88, 230, 30, 30),
    "belt": (131, 230, 60, 30),
    "lrin": (203, 230, 30, 30),
    "feet": (247, 199, 60, 60),
}
THEIR_COLUMNS = {"left": 322, "centre": 716, "right": 300, "gutter": 6, "column": 1350}
DOLL_K = 1                   # #174 v-B2: their 30px cell, literally ("literally the same") — v-B had 1.25
THEIR_HEIGHTS = {            # panel heights, same capture — FIXED: their content is laid out inside them
    ".mp-cp": 628, ".mp-notes": 206, ".mp-stats": 726, ".mp-set": 84,
}
THEIR_EQ = (36, 364)         # the EQUIPMENT panel: their 36px header + their 364px body (400 in their capture)
# ⚠ THE PROSE PANELS ARE A FLOOR, NOT A HEIGHT. Each holds one honest sentence, and a fixed height cut that
# sentence at every width where the words out-grew the box — the MERCENARY note lost its "(v-C)" line at his
# 1120 while this law, reading innerHTML, stayed green. They are their measured height when the words fit and
# taller when they do not. S&W is 57 in their capture (low_2000x1300.png, 182..239). The real-layout law
# (test_the_mule_window_fits_at_every_width.py) proves in a browser that 2000 still renders these heights.
THEIR_PROSE_HEIGHTS = {".mp-prim": 102, ".mp-merc": 80, ".mp-loot": 88, ".mp-sw": 57}
STAT_GROUPS = ["ATTRIBUTES", "DEFENSES", "RESISTANCES", "WEAPON", "SPELLS", "ADVENTURE"]

CUT_START = "  var _MULE_COPY_CAP = 3;"
CUT_END = "  // v210: live re-pack — any assignment change re-tetrises an OPEN mule card\n"
MARKUP = re.compile(r'<div class="vault-detail" id="vault-detail"([^>]*)></div>')
PROBE_START = "// 2) probe the BOARD inside the iframe for a visible overlay; if one is up, feed it the Esc."
PROBE_END = "// 3) nothing on the board — close the shell."


def _src(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def _vault_span():
    s = _src("bible.html")
    assert s.count(CUT_START) == 1, "the packer anchor is not where this law looks"
    assert s.count(CUT_END) == 1, "the re-pack anchor is not where this law looks"
    i = s.index(CUT_START)
    j = s.index(CUT_END, i)
    return s[i:j]


def _static_attrs():
    s = _src("bible.html")
    hits = MARKUP.findall(s)
    assert len(hits) == 1, "expected ONE #vault-detail element in the markup, found %d" % len(hits)
    attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', hits[0]))
    if re.search(r'(^|\s)hidden(\s|$)', re.sub(r'"[^"]*"', '""', hits[0])):
        attrs["hidden"] = ""
    return attrs


HARNESS = r"""
var LISTEN = {}, WLISTEN = {}, switched = [];
function mkEl(attrs){
  var cls = {}, a = {};
  Object.keys(attrs || {}).forEach(function(k){ a[k] = attrs[k]; });
  return { hidden: Object.prototype.hasOwnProperty.call(a, 'hidden'), innerHTML: '', scrollTop: 0, parentElement: null,
    classList: { add: function(c){ cls[c] = 1; }, remove: function(c){ delete cls[c]; }, contains: function(c){ return !!cls[c]; } },
    setAttribute: function(k, v){ a[k] = String(v); }, getAttribute: function(k){ return Object.prototype.hasOwnProperty.call(a, k) ? a[k] : null; },
    removeAttribute: function(k){ delete a[k]; }, querySelector: function(){ return null; } };
}
var box = mkEl(%(attrs)s);
/* every innerHTML write is COUNTED, and '.mp' answers with the layout signature the page wrote — so the resize
   handler's "re-lay only when a layout number moved" is judged on what the shipped code did, not on its source */
var _writes = 0, _html = '';
Object.defineProperty(box, 'innerHTML', { get: function(){ return _html; }, set: function(v){ _html = v; _writes++; } });
box.querySelector = function(sel){
  if (sel !== '.mp') return null;
  var m = /data-sig="([^"]*)"/.exec(_html);
  return m ? { getAttribute: function(k){ return k === 'data-sig' ? m[1] : null; } } : null;
};
var body = { appendChild: function(el){ el.parentElement = body; } };
var document = { body: body, documentElement: mkEl({}),
  getElementById: function(id){ return id === 'vault-detail' ? box : null; },
  querySelector: function(sel){ return sel === '.tab.active' ? { dataset: { tab: 'vault' } } : null; },
  querySelectorAll: function(){ return []; },
  addEventListener: function(n, f){ (LISTEN[n] = LISTEN[n] || []).push(f); } };
var window = { innerWidth: %(w)d, innerHeight: %(h)d, switchTab: function(t){ switched.push(t); },
  addEventListener: function(n, f){ (WLISTEN[n] = WLISTEN[n] || []).push(f); } };
function setTimeout(f){ f(); } function clearTimeout(){}
/* #174 R1 — the routed store the board gives every script (window.LSR), so the per-mule "what is in front" memory is
   driven on the shipped code; %(lsr)s seeds it */
window.LSR = (function(m){ return { getItem: function(k){ return Object.prototype.hasOwnProperty.call(m, k) ? m[k] : null; },
  setItem: function(k, v){ m[k] = String(v); }, dump: function(){ return m; } }; })(%(lsr)s);
var roster = [{ id: 'uni-weap', name: 'UNI-WEAPONS', icon: 'W', note: 'unique melee + caster weapons' },
              { id: 'bases', name: 'SOCKETED', icon: 'S', note: 'socketed bases' },
              { id: 'empty', name: 'EMPTY-ONE', icon: 'E', note: '' },
              { id: 'xss', name: 'X-LOCKER', icon: '<img src=x onerror=alert(1)>', note: '' }];
function muleById(id){ for (var i = 0; i < roster.length; i++) if (roster[i].id === id) return roster[i]; return null; }
var assign = %(assign)s, SIZES = %(sizes)s;
function vaultSize(n){ return SIZES[n] || [2, 4]; }
function tipOf(){ return null; }
function copyCount(){ return 1; }
function art(n){ return '<i class="a">' + n + '</i>'; }
function esc(t){ return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }
function jsArg(t){ return String(t).replace(/\\/g,'\\\\').replace(/'/g,"\\'"); }
function _renderSharedStash(){}
function _itemValue(n){ return ({ 'Windforce': 'high', 'Stone of Jordan': 'med', 'Shako': 'low' })[n] || ''; }
%(span)s
window.openMuleCard(%(mule)s);
if (%(view)s) window._mpSet('view', %(view)s);
var out = { html: box.innerHTML, role: box.getAttribute('role'), modal: box.getAttribute('aria-modal'),
            label: box.getAttribute('aria-label'), hidden: box.hidden, fs: box.classList.contains('vd-fs'),
            on: box.classList.contains('mp-on') };
if (%(page)d >= 0){ window._muleSetPage(%(page)d); out.html2 = box.innerHTML; }
out.writes = [_writes];
%(resize)s.forEach(function(wh){ window.innerWidth = wh[0]; window.innerHeight = wh[1];
  (WLISTEN.resize || []).forEach(function(f){ f({}); }); out.writes.push(_writes); });
out.keys = [];
%(keys)s.forEach(function(k){
  (LISTEN.keydown || []).forEach(function(f){ f({ key: k[0], target: k[1] ? { tagName: k[1] } : null, preventDefault: function(){} }); });
  var m = /Mule (\d+) \/ (\d+)/.exec(box.innerHTML); out.keys.push(m ? Number(m[1]) : null);
});
if (%(esc)s){
  (LISTEN.keydown || []).forEach(function(f){ f({ key: 'Escape', target: null, preventDefault: function(){} }); });
  out.after = { hidden: box.hidden, fs: box.classList.contains('vd-fs'), on: box.classList.contains('mp-on'), switched: switched };
}
%(steps)s
console.log(JSON.stringify(out));
"""

SMALL = {"Windforce": [2, 4], "Stone of Jordan": [1, 1], "Shako": [2, 2], "Arachnid Mesh": [2, 1]}


def _drive(mule="uni-weap", w=2000, h=1300, assign=None, sizes=None, page=-1, esc=False, attrs=None, resize=(), keys=(),
           view=None, lsr=None, steps=""):
    if assign is None:
        assign = dict((n, "uni-weap") for n in SMALL)
    js = HARNESS % {
        "attrs": json.dumps(_static_attrs() if attrs is None else attrs),
        "w": w, "h": h, "assign": json.dumps(assign), "sizes": json.dumps(sizes or SMALL),
        "span": _vault_span(), "mule": json.dumps(mule), "page": page, "esc": "true" if esc else "false",
        "resize": json.dumps([list(x) for x in resize]),
        "keys": json.dumps([list(k) for k in keys]),
        "view": json.dumps(view), "lsr": json.dumps(lsr or {}), "steps": steps,
    }
    # ⚠ #174 v-B2 — THE PROGRAM GOES ON STDIN, NEVER ON ARGV. `node -e <js>` passed the whole cut as ONE argument;
    # Linux caps a single argument at 131,072 bytes (MAX_ARG_STRLEN) and macOS does not, so this law was green on his
    # Mac and could not even start on the CI runner: measured on main 1e1f946e, "FAILED (errors=19)" in 1.5s — the
    # vault span alone was 128,195 bytes. test_the_mule_window_places_by_hand pins every mule-window harness to stdin.
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError("the shipped mule window would not run - UNKNOWN, not passing: %s" % r.stderr[:600])
    return json.loads(r.stdout.strip().splitlines()[-1])


def _unit(html):
    m = re.search(r'<div class="mp[^"]*" style="--u:([0-9.]+)px[;"]', html)
    assert m, "the window carries no --u unit"
    return float(m.group(1))


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheDollIsTheirs(unittest.TestCase):

    def test_the_ten_slots_sit_at_their_measured_rects(self):
        html = _drive()["html"]
        got = {}
        for m in re.finditer(r'data-slot="(\w+)" style="left:calc\((\d+)\*var\(--du\)\);top:calc\((\d+)\*var\(--du\)\);'
                             r'width:calc\((\d+)\*var\(--du\)\);height:calc\((\d+)\*var\(--du\)\)"', html):
            got[m.group(1)] = tuple(int(x) for x in m.groups()[1:])
        self.assertEqual(len(re.findall(r'class="mp-slot', html)), 10, "the doll does not have ten slots")
        self.assertEqual(got, THEIR_SLOTS, "a doll slot left the rect measured off their builder")
        # every slot sits in the doll box, whose origin keeps their 36px header on the window's own unit
        box = html.index('<div class="mp-dollbox">')
        self.assertTrue(box < html.index('data-slot="rarm"') < html.index('<div class="mp-inv">'))

    def test_the_doll_unit_is_their_cell_times_the_upgrade(self):
        """#174 v-B2: their cell, literally (DOLL_K = 1; v-B's 1.25 upgrade is gone). The CSS unit and the script's factor
        are ONE number — the inventory cell is computed from the script's, the slots are drawn on the CSS's. [[copy-drift]]"""
        s = _src("bible.html")
        self.assertEqual(s.count(".mp{--du:calc(%s*var(--u))}" % DOLL_K), 1, "the doll's unit is not %s x --u" % DOLL_K)
        self.assertEqual(s.count("  var MP_DOLL_K = %s;" % DOLL_K), 1, "the script's doll factor is not the CSS's")
        self.assertEqual(s.count(".mp-dollbox{position:absolute;left:0;top:calc(36*var(--u) - 36*var(--du));"), 1,
                         "the doll box no longer keeps their 36px header, so every slot drifts")
        # stacked (a phone), the unit IS the doll's — it already fills the width, so the upgrade is not applied twice
        self.assertEqual(s.count(".mp.mp-stack{--du:var(--u)}"), 1, "a phone applies the desktop doll upgrade on top "
                                                                    "of a unit that already fills its width")

    def test_the_inventory_is_ten_by_four_inside_the_equipment_panel(self):
        """#174 R1: ONE panel holds the doll and its inventory — big in the centre (EQUIPMENT in front) or small at the
        left (anything else in front). Either way the 10x4 grid is under the doll, in the same panel, with the I / II tabs."""
        for view, cls in ((None, 'mp-eq mp-eq-big'), ("stash", 'mp-eq mp-side'), ("calc", 'mp-eq mp-side')):
            html = _drive(view=view)["html"]
            self.assertEqual(html.count('<section class="mp-p mp-eq'), 1, "%s: the doll panel is missing or doubled" % view)
            eq = html.index('<section class="mp-p %s"' % cls)
            end = html.index('</section>', html.index('<div class="mp-inv">', eq))
            inv = html.index('<div class="mp-inv">', eq)
            self.assertTrue(eq < html.index('data-slot="rarm"') < inv < end, "%s: the 10x4 inventory is not under the doll in its panel" % view)
            self.assertEqual(html[inv:end].count('class="vd-cell"'), 40, "%s: the inventory under the doll is not 10x4" % view)
            self.assertEqual(len(re.findall(r'class="mp-swap', html[eq:inv])), 4, "%s: the I / II weapon-swap tabs are gone" % view)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheThreeColumns(unittest.TestCase):

    def test_the_css_carries_their_column_widths(self):
        s = _src("bible.html")
        c = THEIR_COLUMNS
        self.assertEqual(c["left"] + c["gutter"] + c["centre"], 1044)
        self.assertEqual(1044 + c["gutter"] + c["right"], c["column"])
        self.assertEqual(s.count(".mp{display:grid;grid-template-columns:calc(1044*var(--u)) calc(%d*var(--u));"
                                 "column-gap:calc(%d*var(--u));width:calc(%d*var(--u));"
                                 % (c["right"], c["gutter"], c["column"])), 1, "the outer column split moved")
        # v-B: LEFT is their 322 on the doll's unit; the centre takes the rest of their 1044
        self.assertEqual(s.count(".mp-lc{display:grid;grid-template-columns:calc(%d*var(--du)) minmax(0,1fr);"
                                 "column-gap:calc(%d*var(--u));" % (c["left"], c["gutter"])), 1,
                         "the LEFT | CENTRE split is no longer their 322 on the doll's unit | the rest of 1044")

    def test_the_css_carries_their_panel_heights(self):
        s = _src("bible.html")
        for sel, h in THEIR_HEIGHTS.items():
            m = re.findall(r"^" + re.escape(sel) + r"\{height:calc\((\d+)\*var\(--u\)\)", s, re.M)
            self.assertEqual(m, [str(h)], "%s is not the %dpx panel measured off their builder" % (sel, h))
        self.assertEqual(sum(THEIR_EQ), 400)
        self.assertEqual(re.findall(r"^\.mp-eq\{height:([^}]*)\}", s, re.M), ["calc(%d*var(--u) + %d*var(--du))" % THEIR_EQ],
                         "EQUIPMENT is not their 36px header + their 364px body on the doll's unit")

    def test_a_prose_panel_is_a_floor_that_grows_never_a_box_that_cuts(self):
        s = _src("bible.html")
        for sel, h in THEIR_PROSE_HEIGHTS.items():
            m = re.findall(r"^" + re.escape(sel) + r"\{min-height:calc\((\d+)\*var\(--u\)\)\}", s, re.M)
            self.assertEqual(m, [str(h)], "%s must be min-height %d (their height when the words fit, taller when "
                                          "they do not) — a fixed height cuts its sentence" % (sel, h))
            self.assertEqual(re.findall(r"^" + re.escape(sel) + r"\{height:", s, re.M), [],
                             "%s is a fixed height again — the sentence inside it will be cut" % sel)

    def test_the_panels_live_in_their_columns_in_their_order(self):
        # #174 R1 — the left column's first card is whichever of the two is NOT in front
        for view, side in ((None, '<section class="mp-p mp-sstash mp-side"'), ("stash", '<section class="mp-p mp-eq mp-side"')):
            html = _drive(view=view)["html"]
            order = ['<div class="mp-top">', '<section class="mp-p mp-set">', '<div class="mp-left">',
                     side, '<section class="mp-p mp-prim">', '<section class="mp-p mp-merc">',
                     '<section class="mp-p mp-loot">', '<section class="mp-p mp-sw">', '<div class="mp-centre">',
                     '<section class="mp-p mp-cp">', '<section class="mp-p mp-notes">', '<div class="mp-right">',
                     '<section class="mp-p mp-auth">', '<section class="mp-p mp-show">', '<section class="mp-p mp-stats">']
            at = []
            for o in order:
                self.assertEqual(html.count(o), 1, "%s: %s is missing or doubled" % (view, o))
                at.append(html.index(o))
            self.assertEqual(at, sorted(at), "%s: a panel left its column or its place in the column" % view)

    def test_one_unit_their_pixels_at_2000_proportions_at_1280_stacked_under_900(self):
        self.assertEqual(_unit(_drive(w=2000, h=1300)["html"]), 1.0, "at 2000 wide the window is not their pixels")
        k = _unit(_drive(w=1280, h=800)["html"])
        self.assertLess(k, 1.0)
        self.assertLessEqual(THEIR_COLUMNS["column"] * k + 48, 1280.01, "at 1280 the three columns scroll sideways")
        self.assertIn('class="mp mp-stack"', _drive(w=800, h=1000)["html"], "under 900 the columns do not stack")

    def test_the_type_rides_the_unit_with_a_floor(self):
        """A 15px header in a 322*0.72px panel is how the text got cut between 900 and 1250 wide. Every size in
        the window's block is a scaled token; each scaled token is its root token times --kf, floored at the
        smallest step of the scale; and openMuleCard writes --kf = min(1, k) beside --u."""
        s = _src("bible.html")
        a = s.index("/* ══ #174 v-A — THE MULE WINDOW IS THE D2PLANNER BUILDER'S SHELL, IN OUR THEME.")
        b = s.index("/* mule ID card — in-game stash/inventory replica */", a)
        blk = re.sub(r"/\*.*?\*/", " ", s[a:b], flags=re.S)
        sizes = re.findall(r"font-size:([^;}]+)", blk)
        self.assertGreaterEqual(len(sizes), 20, "the window's CSS block carries almost no sizes — the anchor moved")
        raw = [v for v in sizes if not re.match(r"var\(--fs-mp-(display|title|body|meta|micro)\)$", v.strip())]
        self.assertEqual(raw, [], "a size in the mule window does not ride the unit: %s" % raw)
        for t in ("display", "title", "body", "meta"):
            self.assertEqual(blk.count("--fs-mp-%s:max(var(--fs-micro),calc(var(--fs-%s)*var(--kf,1)))" % (t, t)), 1,
                             "--fs-mp-%s is not its token times the unit, floored at --fs-micro" % t)
        self.assertEqual(blk.count("--fs-mp-micro:var(--fs-micro)"), 1)
        for (w, h, kf) in ((2000, 1300, "1.0000"), (1280, 800, "0.9126"), (800, 1000, "1.0000")):
            m = re.search(r'style="--u:[0-9.]+px;--kf:([0-9.]+)"', _drive(w=w, h=h)["html"])
            self.assertTrue(m, "openMuleCard no longer writes --kf beside --u")
            self.assertEqual(m.group(1), kf, "at %dx%d --kf is not min(1, k)" % (w, h))

    def test_a_header_title_and_its_control_have_their_own_columns(self):
        """The Stash button sat position:absolute over a centred title, so a narrower panel slid one under the
        other ("EQUIPMEN" at 920). Title and control each own a grid column now."""
        s = _src("bible.html")
        self.assertEqual(s.count(".mp-h{min-height:calc(36*var(--u));display:grid;grid-template-columns:1fr auto 1fr;"), 1,
                         "the header is no longer nothing | title | control")
        hr = re.findall(r"^\.mp-h-r\{([^}]*)\}", s, re.M)
        self.assertEqual(len(hr), 1)
        self.assertIn("grid-column:3", hr[0])
        self.assertNotIn("position:absolute", hr[0], "the header control floats over the title again")
        html = _drive()["html"]
        heads = re.findall(r'<div class="mp-h">(.{0,40})', html)
        self.assertEqual(len(heads), 10, "the window no longer has its ten panel headers")
        for hd in heads:
            self.assertTrue(hd.startswith('<span class="mp-h-t">'), "a header title is not in its own column: %r" % hd)

    def test_a_resize_re_lays_the_window_only_when_a_layout_number_moves(self):
        """A height-only resize (first seen as a phone keyboard opening) re-rendered the whole window and took the Stats
        search box out from under his typing. The handler compares the layout signature the page wrote.
        v3889 (#132, no phone): driven at desktop sizes only - the 390 keyboard and the 460 / 560 stacked steps left with the
        phone page. Measured 11-09: the deltas below are what the handler writes at these sizes."""
        out = _drive(w=1280, h=800, resize=[(1280, 820), (1280, 800), (1120, 800), (1280, 800), (1280, 695), (880, 900)])
        w = out["writes"]
        self.assertEqual(w[0], 1, "opening the window should write it once")
        self.assertEqual(w[1] - w[0], 0, "a height-only resize that leaves the unit alone re-rendered the window")
        self.assertEqual(w[2] - w[1], 0, "a resize back to the same size re-rendered the window")
        self.assertEqual(w[3] - w[2], 1, "a width that changes the unit did not re-lay the window")
        self.assertEqual(w[4] - w[3], 1, "a width back to the first did not re-lay the window")
        # #174 v-B2 — 1280x695 is his console's board under its header: the height now decides the unit, so the
        # stash panel he packs from fits the window; that resize MUST re-lay it
        self.assertEqual(w[5] - w[4], 1, "a height-only resize that moves the unit (1280x695) did not re-lay the window")
        self.assertEqual(w[6] - w[5], 1, "a width under 900 (Dean's ~800-wide window band) did not re-lay the window")

    def test_the_stash_keeps_our_five_tabs_wherever_it_sits(self):
        for view in (None, "stash"):
            self._five_tabs(view)

    def _five_tabs(self, view):
        html = _drive(view=view)["html"]
        if view == "stash":
            self.assertIn('<div class="mp-view mp-v-stash">', html, "STASH in front does not put the stash in the centre")
            st = html.index('<div class="mp-view mp-v-stash">')
            end = html.index('<div class="mp-view mp-v-tree"', st)
        else:   # #174 R1 — the character in front: the stash is the left column's first card
            st = html.index('<section class="mp-p mp-sstash mp-side"')
            end = html.index('</section>', st)
        # #174 v-B2 — each tab is a CONTROL: a button that switches the grid, the open one marked (v-B: dim labels
        # with nothing behind them, which the Grok seat read as "barely clickable")
        for t in ("Personal", "Shared", "Gems", "Materials", "Runes"):
            m = re.search(r'<button type="button" class="vd-tab( vt-on)?" role="tab" aria-selected="(true|false)" '
                          r'data-tab="%s"[^>]*onclick="window._mpSet\(\'stab\',\'%s\'\)"[^>]*>%s</button>'
                          % (t.lower(), t.lower(), t), html[st:end])
            self.assertTrue(m, "the %s stash tab is not a button that switches the grid" % t)
            self.assertEqual(bool(m.group(1)), t == "Personal", "%s: the open tab is not the one marked" % t)
        self.assertEqual(html[st:end].count('class="vd-cell vd-red"'), 100, "the stash is not 10x10")
        for v in ("equip", "stash", "tree", "calc"):
            self.assertEqual(html.count('data-view="%s"' % v), 1)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheCharacterIsInFront(unittest.TestCase):
    """#174 R1 — his order on v3506's mule window (2026-09-26): "make the equipment here in the front as main front and
    center instead of the stash ... both inventory and character together because the charms are related", and before
    it "enlarge that character as main ... the stash can be smaller on the side". A mule opens with EQUIPMENT in front —
    the doll and its inventory big in the centre, the stash small at the left; STASH swaps them; each mule remembers
    which one he had in front; only a swap animates."""

    def test_a_mule_opens_with_the_doll_and_its_inventory_in_the_centre(self):
        html = _drive()["html"]
        tabs = re.findall(r'<button type="button" role="tab" aria-selected="(true|false)" class="mp-ctab( on)?" data-view="(\w+)"', html)
        self.assertEqual([t[2] for t in tabs], ["equip", "stash", "tree", "calc"], "the centre's tabs are not EQUIPMENT · STASH · SKILL TREE · CALCULATIONS")
        self.assertEqual([t[2] for t in tabs if t[0] == "true" and t[1]], ["equip"], "EQUIPMENT is not the tab in front when a mule opens")
        c = html.index('<div class="mp-centre">')
        v = html.index('<div class="mp-view mp-v-equip">', c)
        self.assertLess(html.index('<section class="mp-p mp-eq mp-eq-big" style="--du:calc(1.45*var(--u))"', v), html.index('<div class="mp-view mp-v-stash"', v),
                        "the big doll panel is not the centre's first view, on the 1.45 unit")
        self.assertIn('<div class="mp-view mp-v-stash" hidden></div>', html,
                      "with the character in front the centre still draws a hidden stash — a second grid a drag or a focus could land in")
        self.assertLess(html.index('<section class="mp-p mp-sstash mp-side"'), c, "the small stash is not in the left column")

    def test_stash_in_front_swaps_the_two_and_both_exist_once_in_every_view(self):
        for view in (None, "stash", "tree", "calc"):
            html = _drive(view=view)["html"]
            self.assertEqual(html.count('class="mp-slot'), 10, "%s: the doll is missing or doubled" % view)
            # the stash is in front or at the side while EQUIPMENT / STASH lead; SKILL TREE and CALCULATIONS keep the doll at
            # the left the way theirs always does, and draw no stash at all — never a hidden one
            st = 1 if view in (None, "stash") else 0
            self.assertEqual(html.count('class="vd-cell'), 40 + 100 * st, "%s: stash 100 (when shown) + inventory 40, once each" % view)
            self.assertEqual(html.count('class="vd-grid"'), 1 + st, "%s: a grid is missing or doubled" % view)
            self.assertEqual(html.count('data-fk="stab-personal"'), st, "%s: the stash tabs are missing or doubled" % view)
            self.assertEqual(html.count('class="mp-p mp-eq mp-eq-big"'), 1 if view is None else 0, "%s: the big doll is on the wrong view" % view)
            enl = re.findall(r'data-fk="enl-(\w+)" onclick="window._mpSet\(\'view\',\'(\w+)\'\)"', html)
            self.assertEqual(enl, [("stash", "stash")] if view is None else [("equip", "equip")],
                             "%s: the side card cannot bring itself to the centre" % view)

    def test_each_mule_remembers_what_he_put_in_front(self):
        steps = r"""
out.mem = [];
var front = function(){ return /class="mp-ctab on" data-view="(\w+)"/.exec(box.innerHTML)[1]; };
window._mpSet('view', 'stash'); out.mem.push(window._mpViewFor('uni-weap'));
window.openMuleCard('bases'); out.mem.push(front());
window.openMuleCard('uni-weap'); out.mem.push(front());
out.store = window.LSR.dump()['d2r_mpView'] || null;
"""
        out = _drive(steps=steps)
        self.assertEqual(out["mem"], ["stash", "equip", "stash"],
                         "a mule does not come back the way he left it, or a mule he never touched does not open on EQUIPMENT")
        self.assertEqual(json.loads(out["store"]), {"uni-weap": "stash"}, "the choice is not kept in the routed store")
        # a store that lies (a view that does not exist) is never trusted: the mule opens on EQUIPMENT
        html = _drive(lsr={"d2r_mpView": json.dumps({"uni-weap": "<img>"})})["html"]
        self.assertIn('class="mp-ctab on" data-view="equip"', html, "a bad remembered view was trusted")

    def test_only_a_swap_fades_and_reduced_motion_never_does(self):
        steps = r"""
var cls = function(){ return /<div class="mp([^"]*)" style/.exec(box.innerHTML)[1]; };
window._mpSet('view', 'stash'); out.swap = cls();
window._mpSet('diff', 'nightmare'); out.again = cls();
window._mpSet('view', 'stash'); out.same = cls();
"""
        out = _drive(steps=steps)
        self.assertIn("mp-anim", out["swap"], "a swap does not fade")
        self.assertNotIn("mp-anim", out["again"], "a re-render that is not a swap fades — every drag would flicker")
        self.assertNotIn("mp-anim", out["same"], "choosing the view already in front fades")
        s = _src("bible.html")
        self.assertEqual(s.count("@media (prefers-reduced-motion:reduce){.mp.mp-anim .mp-view:not([hidden]),.mp.mp-anim .mp-side{animation:none}}"), 1,
                         "the swap ignores his reduced-motion setting")
        m = re.search(r"\.mp\.mp-anim \.mp-view:not\(\[hidden\]\),\.mp\.mp-anim \.mp-side\{animation:mpIn \.(\d+)s", s)
        self.assertTrue(m and int(m.group(1)) <= 20, "the swap is slower than 200ms — smooth, not sluggish")

    def test_the_big_panel_fits_the_centre_under_its_tabs(self):
        """The big panel is their 364-unit body on MP_EQ_BIG; with the count line under it, it must fit the 628 panel
        under its 36 tab band and 8+8 padding. The browser law measures the pixels; this pins the arithmetic."""
        s = _src("bible.html")
        k = float(re.search(r"var MP_EQ_BIG = ([0-9.]+),", s).group(1))
        self.assertLessEqual(364 * k + 2 + 6 + 30, 628 - 36 - 16, "the big doll + inventory + the count line overflow the centre")
        self.assertLessEqual(322 * k, 716 - 20, "the big doll is wider than the centre")
        self.assertGreaterEqual(k, 1.4, "the character is barely bigger than the side card — not 'front and center'")


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class EveryEmptyPanelSaysWhy(unittest.TestCase):

    def test_every_stat_is_unknown_with_a_reason(self):
        html = _drive()["html"]
        groups = re.findall(r'<div class="mp-st-g">([A-Z]+)', html)
        self.assertEqual(groups, STAT_GROUPS)
        rows = re.findall(r'<div class="mp-st-r" data-k="[^"]*"><span>([^<]+)</span>'
                          r'<span class="mp-unk" title="UNKNOWN — ([^"]+)">([^<]*)</span></div>', html)
        self.assertEqual(len(rows), html.count('class="mp-st-r"'), "a stat row does not have the UNKNOWN shape")
        self.assertGreaterEqual(len(rows), 20)
        for label, why, val in rows:
            self.assertEqual(val, "UNKNOWN", "%s shows %r - a locker has no measured stat" % (label, val))
            self.assertGreater(len(why.strip()), 10, "%s is UNKNOWN without saying why" % label)
        self.assertEqual(len(re.findall(r'<div class="mp-st-why">[^<]{10,}</div>', html)), len(STAT_GROUPS))

    def test_the_panels_nothing_fills_say_what_would(self):
        html = _drive()["html"]
        for sec in ("mp-prim", "mp-merc", "mp-loot", "mp-sw"):
            i = html.index('<section class="mp-p %s">' % sec)
            body = html[i:html.index("</section>", i)]
            self.assertIn("Nothing fills this yet.", body, sec)
            self.assertRegex(body, r"\((v-[A-E]|not scheduled)[^)]*\)", "%s does not say what would fill it" % sec)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheOldBehaviourSurvives(unittest.TestCase):

    def test_packing_counts_and_the_readouts_the_ci_specs_read(self):
        out = _drive()
        html = out["html"]
        self.assertEqual(html.count('class="vd-cell'), 140, "stash 100 + inventory 40")
        self.assertEqual(html.count('class="vd-grid"'), 2)
        self.assertEqual(html.count('class="vd-item'), len(SMALL))
        self.assertIn('<span class="vd-name">UNI-WEAPONS</span>', html)
        self.assertRegex(html, r'<span class="vd-sub">4 items total')
        self.assertIn(" on this mule</div>", html)
        self.assertIn('class="vd-close" onclick="window.vaultCloseCard()"', html)
        self.assertEqual(html.count('<div class="vd-list">'), 1)
        self.assertTrue(out["fs"] and out["on"] and not out["hidden"])

    def test_an_empty_locker_says_so(self):
        self.assertIn("empty locker", _drive(mule="empty")["html"])

    def test_a_big_locker_spills_onto_mule_tabs_and_pages(self):
        names = ["Base %d" % i for i in range(60)]
        out = _drive(mule="bases", assign=dict((n, "bases") for n in names),
                     sizes=dict((n, [2, 4]) for n in names), page=1)
        html, html2 = out["html"], out["html2"]
        n = int(re.search(r"Mule 1 / (\d+)", html).group(1))
        self.assertGreaterEqual(n, 2)
        self.assertEqual(len(re.findall(r'class="mp-settab(?: on)?" onclick="window._muleSetPage\(\d+\)"', html)), n,
                         "the BUILD SET row does not carry one tab per mule")
        self.assertIn('class="mp-settab on" onclick="window._muleSetPage(0)"', html)
        self.assertIn('class="mp-settab on" onclick="window._muleSetPage(1)"', html2, "paging did not move the tab")
        self.assertIn("Mule 2 / %d" % n, html2)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheReviewsLowFindingsStayFixed(unittest.TestCase):
    """#174 v-A review (2026-09-25): four low findings the fix round did not list, fixed on main and pinned here."""

    def _big(self, keys):
        names = ["Base %d" % i for i in range(60)]
        return _drive(mule="bases", assign=dict((n, "bases") for n in names),
                      sizes=dict((n, [2, 4]) for n in names), keys=keys)

    def test_arrow_keys_step_the_mules(self):
        self.assertEqual(self._big([("ArrowRight", None)])["keys"], [2], "ArrowRight did not step to Mule 2")

    def test_arrow_keys_in_a_text_field_are_his_caret_not_a_page_turn(self):
        self.assertEqual(self._big([("ArrowRight", "INPUT")])["keys"], [1],
                         "typing in the Stats search turned the mule page")

    def test_a_locker_icon_is_escaped(self):
        html = _drive(mule="xss", assign={})["html"]
        self.assertNotIn("<img src=x", html, "a roster icon reached the page as markup")
        self.assertIn("&lt;img src=x", html)

    def test_the_value_count_uses_tiers_that_exist(self):
        html = _drive()["html"]
        self.assertIn("Trade value (high · med)", html, "the calculations row names a tier ITEM_VALUE never has")
        self.assertIn("1 · 1", html)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class EscClosesTheWindowNotTheShell(unittest.TestCase):

    def test_the_markup_declares_a_dialog(self):
        a = _static_attrs()
        self.assertEqual(a.get("role"), "dialog", "the console's Esc probe cannot see #vault-detail")
        self.assertEqual(a.get("aria-modal"), "true")
        self.assertTrue(a.get("aria-label"), "a dialog with no name")
        self.assertIn("hidden", a, "the window must start closed, or the probe would forward every Esc to it")

    def test_opening_declares_the_dialog_even_on_markup_that_lost_it(self):
        out = _drive(attrs={"class": "vault-detail", "id": "vault-detail", "hidden": ""})
        self.assertEqual(out["role"], "dialog")
        self.assertEqual(out["modal"], "true")
        self.assertIn("UNI-WEAPONS", out["label"] or "")

    def test_escape_closes_the_window_and_returns_to_the_vault(self):
        out = _drive(esc=True)
        self.assertEqual(out["after"], {"hidden": True, "fs": False, "on": False, "switched": ["vault"]})

    def test_the_console_probe_still_forwards_to_a_dialog(self):
        ui = _src("tv/control_ui.html")
        self.assertEqual(ui.count(PROBE_START), 1)
        i = ui.index(PROBE_START)
        blk = ui[i:ui.index(PROBE_END, i)]
        self.assertIn("fd.querySelectorAll(", blk)
        self.assertIn(', [role="dialog"]:not([hidden])\');', blk,
                      "the console's Esc probe no longer recognises a dialog, so Esc would close the shell again")
        self.assertIn("w.document.dispatchEvent(new w.KeyboardEvent('keydown', { key:'Escape', bubbles:true }))", blk)


if __name__ == "__main__":
    unittest.main(verbosity=2)


RED_PROOF = [
    {
        "why": "#174 R1 - a mule opens with the STASH in front again, the doll a small card at the left (his screenshot)",
        "file": "bible.html",
        "find": "  function _mpViewFor(id){ var v = _mpViewBy && _mpViewBy[id]; return MP_VIEWS[v] ? v : 'equip'; }\n",
        "replace": "  function _mpViewFor(id){ var v = _mpViewBy && _mpViewBy[id]; return MP_VIEWS[v] ? v : 'stash'; }\n",
        "matches": 1,
    },
    {
        "why": "#174 R1 - the centre draws a hidden stash twin behind EQUIPMENT (two grids, two sets of tabs)",
        "file": "bible.html",
        "find": "      +   (_mpView === 'stash'\n",
        "replace": "      +   (true\n",
        "matches": 1,
    },
    {
        "why": "#174 R1 - a mule forgets what he put in front",
        "file": "bible.html",
        "find": "    _mpViewBy[id] = v;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 R1 - every re-render fades, so a drag or a difficulty change flickers the window",
        "file": "bible.html",
        "find": "    var _anim = _mpAnim; _mpAnim = false;",
        "replace": "    var _anim = true; _mpAnim = false;",
        "matches": 1,
    },
    {
        "why": "#174 R1 - the swap ignores reduced motion",
        "file": "bible.html",
        "find": "@media (prefers-reduced-motion:reduce){.mp.mp-anim .mp-view:not([hidden]),.mp.mp-anim .mp-side{animation:none}}",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 review - arrow keys typed into the Stats search turn the mule page again",
        "file": "bible.html",
        "find": "             && !(e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName || ''))){\n",
        "replace": "             ){\n",
        "matches": 1,
    },
    {
        "why": "#174 review - a roster icon reaches the mule window header as raw markup",
        "file": "bible.html",
        "find": "<span class=\"vd-icon\">'+esc(m.icon||'📦')+'</span><span class=\"vd-name\">'+esc(m.name)+_muleLabel",
        "replace": "<span class=\"vd-icon\">'+(m.icon||'📦')+'</span><span class=\"vd-name\">'+esc(m.name)+_muleLabel",
        "matches": 1,
    },
    {
        "why": "#174 review - the value row counts a 'vhigh' tier that ITEM_VALUE never returns (a fabricated 0)",
        "file": "bible.html",
        "find": "      _tiers = { high: 0, med: 0 };\n",
        "replace": "      _tiers = { high: 0, med: 0, vhigh: 0 };\n      _tiers.med = undefined;\n",
        "matches": 1,
    },
    {
        "why": "#174 - the mule window's markup is not a dialog, so the console's Esc probe sends him HOME",
        "file": "bible.html",
        "find": '<div class="vault-detail" id="vault-detail" role="dialog" aria-modal="true" '
                'aria-label="Mule window (Esc closes)" hidden></div>',
        "replace": '<div class="vault-detail" id="vault-detail" hidden></div>',
        "matches": 1,
    },
    {
        "why": "#174 - opening the window no longer declares the dialog, so markup that lost it stays invisible",
        "file": "bible.html",
        "find": "    box.setAttribute('role', 'dialog'); box.setAttribute('aria-modal', 'true');\n",
        "replace": "    box.setAttribute('aria-modal', 'true');\n",
        "matches": 1,
    },
    {
        "why": "#174 - a doll slot drifts off the rect measured on their builder (helm grows to 60x90)",
        "file": "bible.html",
        "find": "    ['head', '⛑',    'helm',               131,  50, 60,  60],\n",
        "replace": "    ['head', '⛑',    'helm',               131,  50, 60,  90],\n",
        "matches": 1,
    },
    {
        "why": "#174 - a locker's stats render a made-up 0 instead of UNKNOWN",
        "file": "bible.html",
        "find": "return '<span class=\"mp-unk\" title=\"UNKNOWN — '+why+'\">UNKNOWN</span>'; };",
        "replace": "return '<span class=\"mp-unk\" title=\"UNKNOWN — '+why+'\">0</span>'; };",
        "matches": 1,
    },
    {
        "why": "#174 - the LEFT column stops being their 322px (proportions lost)",
        "file": "bible.html",
        "find": ".mp-lc{display:grid;grid-template-columns:calc(322*var(--du)) minmax(0,1fr);",
        "replace": ".mp-lc{display:grid;grid-template-columns:calc(360*var(--du)) minmax(0,1fr);",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the doll leaves their literal geometry again (v-B's 1.25x upgrade comes back: LEFT 402, not their 322)",
        "file": "bible.html",
        "find": ".mp{--du:calc(1*var(--u))}",
        "replace": ".mp{--du:calc(1.25*var(--u))}",
        "matches": 1,
    },
    {
        "why": "#174 - the 10x4 inventory leaves the EQUIPMENT panel",
        "file": "bible.html",
        "find": "'<div class=\"mp-inv\">' + gridHtml(inv.placed, MULE_INV_W, MULE_INV_H, big ? Math.max(14, Math.floor(30 * MP_DOLL_K * _eqK * k) - 2) : invCell, _gOpt('inv')) + '</div>'",
        "replace": "'<div class=\"mp-inv\"></div>'",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the stash tabs are dim labels again that switch nothing (the Grok seat: barely clickable)",
        "file": "bible.html",
        "find": "        onclick: \"window._mpSet('stab','\" + t + \"')\",",
        "replace": "        onclick: \"\",",
        "matches": 1,
    },
    {
        "why": "#174 v-B2 - the unit answers the width alone again, so at 1280 in the console the stash he packs from runs off the bottom",
        "file": "bible.html",
        "find": "return { stack: false, k: Math.min(grow, (vw - 48) / MP_COL_W, Math.max(MP_K_FLOOR, (vh - MP_PAD_V) / MP_WORK_H)) };",
        "replace": "return { stack: false, k: Math.min(grow, (vw - 48) / MP_COL_W) };",
        "matches": 1,
    },
    {
        "why": "#174 - a prose panel is a fixed height again, so the sentence inside it is cut where it out-grows it",
        "file": "bible.html",
        "find": ".mp-loot{min-height:calc(88*var(--u))}\n",
        "replace": ".mp-loot{height:calc(88*var(--u))}\n",
        "matches": 1,
    },
    {
        "why": "#174 - the scaled meta type loses its floor, so a narrow window renders notes below the smallest token",
        "file": "bible.html",
        "find": "--fs-mp-meta:max(var(--fs-micro),calc(var(--fs-meta)*var(--kf,1)))",
        "replace": "--fs-mp-meta:calc(var(--fs-meta)*var(--kf,1))",
        "matches": 1,
    },
    {
        "why": "#174 - the header control floats over a centred title again (the Stash button over EQUIPMENT)",
        "file": "bible.html",
        "find": ".mp-h-r{grid-column:3;justify-self:end;",
        "replace": ".mp-h-r{position:absolute;right:calc(6*var(--u));top:50%;transform:translateY(-50%);",
        "matches": 1,
    },
    {
        "why": "#174 - every resize re-renders the window, so a phone keyboard takes the search box from under his typing",
        "file": "bible.html",
        "find": "      if (mp && mp.getAttribute('data-sig') === _mpLayout(window.innerWidth || 1440, window.innerHeight || 900).sig) return;\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "#174 - Esc no longer closes the mule window",
        "file": "bible.html",
        "find": "    if (e.key==='Escape' && openMuleId){ window.vaultCloseCard(); }\n",
        "replace": "    if (e.key==='Esc_' && openMuleId){ window.vaultCloseCard(); }\n",
        "matches": 1,
    },
]
