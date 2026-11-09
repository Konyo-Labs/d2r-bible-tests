# -*- coding: utf-8 -*-
"""#174 v-B2 — THE CHARACTER BUILDER FITS AT EVERY WIDTH, MEASURED IN A REAL BROWSER, NOT READ FROM ITS HTML.

The node law (test_the_character_builder_is_their_builder) proves what the builder SAYS; only layout can prove it is
SEEN. The mule window taught the class, in this same room: every length on the unit and the type fixed, so between
900 and 1250 wide words were cut while innerHTML carried them whole (test_the_mule_window_fits_at_every_width). This
builder is a new window with new words — a doll that fills the centre, a modal that must never hide the slot it
serves, a stats column, an inventory — so it is measured the same way, from the first ship.

WHAT IS MEASURED, per width (2000x1300, 1280x800, 1120x628, 1024x768, 901x900, 800x1000, 375x812), in FIVE states:
the template as it opens · with Crown of Ages on the doll and Annihilus in the inventory · the helm's picker open
(Select) · the helm in Edit (the roll boxes) · the stash list open.
  · no text node in the window is cut by an overflow:hidden/clip ancestor, or lies outside its panel unless a
    scroller holds it; no CONTROL has its box sliced by what contains it
  · nothing scrolls sideways, and the window itself never does
  · no panel header's title runs into its control
  · the modal lies inside the viewport, and in the column layouts it never covers the slot it serves: the glowing
    slot's centre hit-tests to the slot (their helm glows beside their modal, 01_helm_clicked)
  · at 2000x1300 the columns are their LITERAL 322 | 716 | 300 with 6px gutters (spec §1, ±4px), the doll fills the
    716 centre, and the header type is its token (k = 1)
#174 v-B2 FIX ROUND, by real input: at 375 and 2000 the picker's list scrolls to its LAST row under a real wheel
(Weapons, 600+ rows; Boots) - at 375 the stacked pane was unbounded, the list grew to 8715px and only ~35 rows could
ever be reached; and an ACTIVE gold button under the pointer keeps its dark label (Set 1, ! Quests, Filters, the
chosen class - the hover rule painted gold text on the gold face).
#174 v-B3: at 2000 / 1280 / 375 the Edit tab of a BASE with its picked mods - a rare Diadem with four (Devil's, Ruby,
of the Magus, of the Tiger), shut and with ADD MOD open; a magic Grand Charm with Chaotic + of Vita, and with Chaotic
alone and ADD MOD open (its suffixes listed) - nothing cut, nothing outside its panel, nothing sideways, the modal on
screen and off the glowing slot, every picked mod drawn and the open list full of options.
#174 v-B3 FIX ROUND: the open ADD MOD list lies wholly inside the Edit tab's visible box and, with more options than
fit, runs to its bottom (a fixed calc(330 x u) ran ~137px below the modal at 1280x800 and stopped at 158px on a phone
with ~220px empty under it); and ADD MOD is a combobox by REAL keys at 2000 - "res" typed, ArrowDown, Enter: focus stays
in the search box, aria-activedescendant names the second option, which is the one painted, and Enter adds exactly it.
The entry is REAL INPUT: the Tools tab and the Character Builder card are pressed by CDP mouse events at their
centres, each hit-tested first; the helm is equipped the same way (the slot, the search box, the row), a roll is
typed with key events, and the charm is DRAGGED to another cell with a press, moves carrying buttons=1, a release.
#174 v-B4 - THE CHARACTER/INVENTORY TEMPLATE IS ONE PANEL (his order 2026-09-26: "the INVENTORY under the equipment
need to be structured like this JUST LIKE IT IS IN GAME one to one", "they always open and are seen as a set together").
Theirs (planner 60/61, 15_crop): one carved-stone panel, the doll and flush under it the 10x4 grid - black cells, thin
lines, no gaps, no rounded corners. Ours was a framed doll, a caption, then a separate grid with 2px gaps and rounded
gradient cells. Measured in every plain and worn state at the 7 widths AND with three charms placed through the
builder's own picker (Annihilus 1x1, a Grand Charm 1x3, Gheed's Fortune 1x3, their ids read from the database by name)
at 2000x1300 / 1280x800 / 1120x800 / 900x800 / 375x812: the grid and the doll lie inside the ONE panel; the grid's top is
within 12px of the doll's bottom with no word between them; the caption and the status line are under the panel;
10 columns x 4 rows of equal SQUARE cells edge to edge (gap 0), radius 0; the grid never wider than the doll's inner
width; cells >= 26px from 1280 up; every item's rect inside the cells it occupies, with its art; and the charms MOVE
the stats (All Skills and Strength differ from the same build before them).
#174 v-B4 FIX ROUND (two reproduced review findings):
  · AN ITEM'S TILE IS COLOURED BY ITS STATE, NEVER BY ITS QUALITY. Ours filled a unique tile gold with a gold border and a
    gold halo, a magic one blue. Theirs and the game (73_anni_tip, 15_after_drag_crop, sampled) draw a unique Annihilus,
    a unique Hellfire Torch and a magic charm on ONE indigo, (8,2,28) over the black cell, no frame, no halo; only the
    item being edited is green, (6,26,2). With the three charms at the build's own level: every tile one fill whatever
    its data-q (two qualities at least, printed), that fill over the cell within 6 of theirs, no visible border, no art
    filter; a tile pressed by REAL input goes green (theirs within 6) while the others keep the indigo.
  · A CHARM THE LEVEL CANNOT USE IS RED AND COUNTS FOR NOTHING. In the game a charm below its level requirement gives no
    bonus and its background turns red; ours kept the tile gold and STATS summed it (Annihilus req 70 at level 50: All
    Skills 1 EXACT). Every tile is red exactly when the Required Level its own tooltip prints is above the build's level,
    at three levels: the input's max, Gheed's Fortune's requirement (Annihilus's is above it - read, never typed, and
    printed), and one lower by a REAL press of the level's down arrow. At Gheed's level STATS' All Skills is the build's
    own again (Annihilus left out) while Gold Find is what it was at the max (Gheed's still counted); one lower Gold Find
    moves too; STATS names each left-out charm with its level, and Calculations lists it among the failed requirements.
    The SIBLING on the doll, same rule: its slot was already red above the level and STATS summed the item anyway, so the
    fresh build also wears Crown of Ages (its Required Level read from its tooltip, above Gheed's): red and named as left
    out exactly when the level is below it.
The fixture's fresh build is made at its level input's own max, so the charms it places can be used.
#29(d) ROUND 9 (his answers 2026-09-28, "TIGHTEN"), in every Edit state at every width (the helm at the 7 widths, the
rare Diadem and the magic Grand Charm at 2000 / 1280 / 375):
  · THE EDIT WINDOW IS AS TALL AS WHAT IT HOLDS: no more than 12px of its body lies empty under its last line (a fixed
    750-unit frame left ~40px under the helm at 2000, ~340px under a charm, ~230px on a 375 phone), and when it does
    scroll inside itself no more than 12px of the glass is free under it (at 901x900 it scrolled 97px of the helm with
    ~260px of glass unused).
  · THE BUILDER'S TABS STAY IN VIEW WHILE IT IS OPEN: in every state with a modal (Select, Edit, the stash, an inventory
    cell's picker, the mod states) and the tab row on the glass, the modal does not overlap the Equipment | Skill Tree |
    Calculations row and each tab's centre hit-tests to that tab (at 1280x800 the Edit window's top was pulled to 108 and
    covered EQUIPMENT; on a phone the sheet covered the whole glass).
  · (superseded by round 2, REG-1379) no empty band under the builder, which round 1 met by stretching the last panels.
#29 ROUND 2 (2026-09-28, the adversarial review of round 1, each finding reproduced on fe817ab7):
  · REG-1376 HIS WORDS COST NO LINE: "cap 75%" (his ruling, kept) is wider than the "≤75%" it replaced and widened the value's
    column, so a label beside it wrapped once more (Physical Damage Reduction 2 -> 3 lines at 1280x800, Lightning Resistance
    1 -> 2 at 1280 and 2000). At every width, plain and with the helm worn: every capped row's label has the lines it has with
    the cap chip taken away, the chip is one line and lies inside its row; 1280x800 and 901x900 are required.
  · REG-1379 "Tighten both": THE BUILDER IS AS TALL AS WHAT IT HOLDS - round 1 filled the band under it by stretching
    STRENGTHS AND WEAKNESSES and NOTES into empty boxes. At every width, plain and worn: where the window does not scroll it
    ends under its content by its own bottom padding (no band) and STATS ends with the columns beside it (it was the glass's
    height whatever stood there); where it scrolls it is the glass's height; in columns STRENGTHS AND WEAKNESSES and NOTES are
    no taller than their own content (or their floors) with every stretch taken away.

⚠ ITS OWN BROWSER, ON ITS OWN PORT, killed by the handle it holds (render_check._chrome_up / _chrome_down).
⚠ NO CHROME ON THIS MACHINE = a DECLARED skip (exit 77), never a pass.
#42 - A PUSH-TIME RED-PROOF MEASURES ONLY WHERE ITS DEFECT SHOWS (tv/law_widths.py). TV_LAW_WIDTHS, set only by
`heart2.py --prove --push` from a proof's own measured "widths", restricts every width loop and every one-viewport pass
(the keyboard, pointer, hover and tile passes at 2000x1300, the indent at 1280x800) to those viewports; a case whose
viewports are all outside it is a declared SKIP, and each PREMISE counts over the viewports measured (its per-width rate
unchanged). The fixture's own steps - the entry, the equip, the Diadem set before the sweep, the fresh build - run
whatever the restriction, so a restricted run meets each measured state as the full run does. Unset (run_gates, CI,
every run without --push), this law is exactly what it was.
RED_PROOF below.
"""
import io
import json
import os
import socket
import sys
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass


def _free_port():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


# ⚠ BEFORE the import: render_check reads its port once, at import time. A free port by default; TV_LAW_PORT pins one
# when the caller owns a port range (parallel builders each given their own) - never 9222/9223, which are his.
_LAW_PORT = os.environ.get("TV_LAW_PORT", "").strip()
os.environ["TV_RENDER_PORT"] = _LAW_PORT if _LAW_PORT.isdigit() and _LAW_PORT not in ("9222", "9223") else str(_free_port())
import render_check as RC  # noqa: E402
import law_widths as LW  # noqa: E402  #42 - the one reader of TV_LAW_WIDTHS

NO_BROWSER = "no Chrome/Chromium on this machine, so the character builder was not rendered"
WIDTHS = ((2000, 1300), (1280, 800), (1120, 628), (1024, 768), (901, 900), (800, 1000))   # v3889 #132: no 375
#: #174 v-B4 - "invpick": an inventory cell's picker (Select) at every width - the grid moved into the template panel, so
#: where that picker opens moved with it, and the round-7 fallback it can still reach is at 1024 and 901, not 1120-1280
STATES = ("plain", "worn", "picker", "edit", "stash", "invpick")
#: #174 v-B3 - the Edit tab of a base with its picked mods, and with ADD MOD open, at these widths
MOD_WIDTHS = ((2000, 1300), (1280, 800))
#: #174 v-B2 fix round - the picker's list under a real wheel, at 2000 (v3889 #132: the phone width left)
WHEEL_WIDTHS = ((2000, 1300),)
_DIADEM = ("window._cbOpenPick('slot','head'); window._cbChoose('b:ci3'); window._cbQuality('rare');"
           " ['p712','p374','s175','s316'].forEach(function(i){ window._cbAddMod(i); });")
_GC = "window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm3'); window._cbAddMod('p700');"
#: a magic charm with its prefix AND suffix is full (nothing left to list), so its open ADD MOD carries the prefix only
MOD_JS = {"mods": _DIADEM, "addmod": _DIADEM + " window._cbModOpen(true);",
          "gcmods": _GC + " window._cbAddMod('s338');", "gcaddmod": _GC + " window._cbModOpen(true);"}
MOD_STATES = ("mods", "addmod", "gcmods", "gcaddmod")
MOD_ROWS = {"mods": 4, "addmod": 4, "gcmods": 2, "gcaddmod": 1}
#: their builder at 2000 wide (spec §1): the three columns relative to the content column
THEIR_COLS = {"left": (0, 322), "main": (328, 716), "stats": (1050, 300)}
TOL = 4.0
#: #174 v-B4 - the widths the template is measured at with three charms placed (the builder's supported sizes)
TPL_WIDTHS = ((2000, 1300), (1280, 800), (1120, 800), (900, 800))
#: three charms by NAME (the ids are read from the database at run time) at their cells: 1x1, 1x3, 1x3
TPL_CHARMS = (("Annihilus", 0, 0, None), ("Grand Charm", 2, 0, "b:"), ("Gheed's Fortune", 4, 1, None))
#: their grid under their doll, measured (60/61, 15_crop): flush, ~9px of stone, no caption between
TPL_FLUSH = 12.0
TPL_MIN_CELL = 26.0
#: #174 v-B4 fix round - THEIR tile fills, sampled with PIL from their own screenshot at 2000 wide (73_anni_tip: the
#: unique Annihilus and Hellfire Torch and 15_after_drag_crop's magic charm alike; the Grand Charm open in Edit is green),
#: as the colour seen over the black cell - ours is composited over OUR cell the same way before it is compared
THEIR_TILE = (8, 2, 28)
THEIR_EDITED = (6, 26, 2)
TILE_TOL = 6

#: #174 v-B4 - the template: the ONE panel (#cb-eqp), its doll (#cb-doll) and its grid (#cb-inv), every cell, every item
TEMPLATE = r"""(function(){ try {
  var d = document, box = d.getElementById('cb-win'), cb = box && box.querySelector('.cb');
  if (!cb || box.hidden) return JSON.stringify({ err: 'the builder did not render' });
  var P = d.getElementById('cb-eqp'), D = d.getElementById('cb-doll'), G = d.getElementById('cb-inv');
  if (!P || !D || !G) return JSON.stringify({ err: 'no template: panel ' + !!P + ', doll ' + !!D + ', grid ' + !!G });
  var R = function(e){ var r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  var pr = R(P), dr = R(D), gr = R(G), gs = getComputedStyle(G);
  var out = { panel: pr, doll: dr, grid: gr, dollInner: D.clientWidth, gridInDom: P.contains(G), dollInDom: P.contains(D),
    gap: [gs.columnGap, gs.rowGap], radius: [gs.borderTopLeftRadius, gs.borderTopRightRadius, gs.borderBottomRightRadius, gs.borderBottomLeftRadius],
    cols: [], rows: [], cellRadius: [], cellW: [], cellH: [], nCells: 0, between: [], below: {}, items: [], stack: cb.classList.contains('cb-stack') };
  var cells = G.querySelectorAll('.cb-cell'), at = {}; out.nCells = cells.length;
  [].forEach.call(cells, function(c){
    var r = R(c), s = getComputedStyle(c), x = +c.getAttribute('data-x'), y = +c.getAttribute('data-y');
    at[x + ',' + y] = r; out.cellW.push(r[2] - r[0]); out.cellH.push(r[3] - r[1]);
    var rad = [s.borderTopLeftRadius, s.borderTopRightRadius, s.borderBottomRightRadius, s.borderBottomLeftRadius].join(' ');
    if (out.cellRadius.indexOf(rad) < 0) out.cellRadius.push(rad);
  });
  var cb0 = [1e9, 1e9, -1e9, -1e9]; Object.keys(at).forEach(function(k){ var q = at[k];
    cb0 = [Math.min(cb0[0], q[0]), Math.min(cb0[1], q[1]), Math.max(cb0[2], q[2]), Math.max(cb0[3], q[3])]; });
  out.cellsBox = cb0;   /* the cells' OWN extent: a grid box can be clamped narrower while its cells overflow it */
  for (var x = 0; x < 10; x++) if (at[x + ',0']) out.cols.push([at[x + ',0'][0], at[x + ',0'][2]]);
  for (var y = 0; y < 4; y++) if (at['0,' + y]) out.rows.push([at['0,' + y][1], at['0,' + y][3]]);
  /* every word drawn between the doll's bottom and the grid's top, over the grid's width */
  var tw = d.createTreeWalker(cb, NodeFilter.SHOW_TEXT), n;
  while ((n = tw.nextNode())){
    var t = n.textContent.trim(); if (!t) continue;
    var el = n.parentElement; if (!el || el.closest('[hidden]')) continue;
    var cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    var rg = d.createRange(); rg.selectNodeContents(n); var rr = rg.getBoundingClientRect(); if (rr.width < 0.5 || rr.height < 0.5) continue;
    var cy = (rr.top + rr.bottom) / 2;
    if (cy > dr[3] - 0.5 && cy < gr[1] + 0.5 && rr.right > gr[0] && rr.left < gr[2]) out.between.push(t.slice(0, 48));
  }
  var ds = box.querySelector('.cb-view:not([hidden]) .cb-doll-say'), is = d.getElementById('cb-inv-say');
  out.below = { caption: ds ? R(ds) : null, status: is ? R(is) : null, captionInPanel: !!(ds && P.contains(ds)), statusInPanel: !!(is && P.contains(is)) };
  [].forEach.call(G.querySelectorAll('.cb-it'), function(it){
    var a = String(it.getAttribute('data-at') || '').split(',').map(Number), r = R(it);
    var c0 = at[a[0] + ',' + a[1]], c1 = at[(a[0] + a[2] - 1) + ',' + (a[1] + a[3] - 1)];
    out.items.push({ at: a, rect: r, cells: c0 && c1 ? [c0[0], c0[1], c1[2], c1[3]] : null,
      name: String(it.getAttribute('aria-label') || '').split(' at ')[0], art: !!it.querySelector('img') });
  });
  var st = {}; [].forEach.call(box.querySelectorAll('.cb-st-r'), function(r){ var l = r.querySelector('.cb-sl'), v = r.querySelector('.cb-sv');
    if (l && v) st[l.textContent.trim()] = v.textContent.trim(); });
  out.stats = { allSkills: st['All Skills'] == null ? null : st['All Skills'], strength: st['Strength (items)'] == null ? null : st['Strength (items)'] };
  return JSON.stringify(out);
 } catch (e) { return JSON.stringify({ err: String(e) }); } })()"""
#: a fresh build through the builder's own "+ New build" (the first class the database lists), so its inventory is empty.
#: #174 v-B4 fix round - made at its level input's OWN max: at the old level 1 the charms it places cannot be used, and
#: a law that saw them move STATS there was asserting the defect
TPL_NEW = ("(function(){ window.closeCharBuilder(); window.openCharBuilder(); window._cbOpenNew();"
           " var c = document.querySelector('#cb-modal .cb-new-cls .cb-btn'); if (!c) return 'no class button'; c.click();"
           " var lv = document.getElementById('cb-new-lvl'); if (!lv || !lv.max) return 'no level field'; window._cbNewLvl(lv.max);"
           " window._cbNewGo(); return 'ok'; })()")
#: #174 v-B4 fix round - every inventory tile's STATE as drawn (its fill, its frame, its art's filter, red / edited) beside
#: the Required Level its own tooltip prints, the cell it sits on, STATS' rows and the notes of what STATS left out
TILES = r"""(function(){ try {
  var d = document, b = window._cbAll()[window._cbState().bid];
  if (!b) return JSON.stringify({ err: 'no saved build is selected' });
  var s = b.sets[b.active | 0], G = d.getElementById('cb-inv'), c0 = G && G.querySelector('.cb-cell');
  var out = { level: b.level | 0, cellBg: c0 ? getComputedStyle(c0).backgroundColor : null, tiles: [], stats: {}, notes: [] };
  [].forEach.call(G ? G.querySelectorAll('.cb-it') : [], function(t){
    var e = s.inv[+t.getAttribute('data-i')], it = e && window._cbItem(e.id), cs = getComputedStyle(t), img = t.querySelector('img');
    var tip = it ? window._cbTipEntry(e, it, b.level | 0, 'inv', b.cls) : null;
    out.tiles.push({ name: e ? e.name : null, q: t.getAttribute('data-q'), need: (tip && tip.reqs && tip.reqs.lvl) || 0,
      red: t.classList.contains('cb-red'), sel: t.classList.contains('cb-sel'), bg: cs.backgroundColor,
      border: [cs.borderTopWidth, cs.borderTopColor], filter: img ? getComputedStyle(img).filter : null, label: t.getAttribute('aria-label') || '' });
  });
  [].forEach.call(d.querySelectorAll('#cb-win .cb-st-r'), function(r){ var l = r.querySelector('.cb-sl'), v = r.querySelector('.cb-sv');
    if (l && v) out.stats[l.textContent.trim()] = v.textContent.trim(); });
  [].forEach.call(d.querySelectorAll('#cb-win .cb-st-note'), function(n){ out.notes.push(n.textContent.trim()); });
  out.worn = Object.keys(s.slots || {}).map(function(k){ var e = s.slots[k], it = window._cbItem(e.id), el = d.querySelector('#cb-doll .cb-slot[data-slot="' + k + '"]');
    var tip = it ? window._cbTipEntry(e, it, b.level | 0, k, b.cls) : null;
    return { slot: k, name: e.name, need: (tip && tip.reqs && tip.reqs.lvl) || 0, red: !!(el && el.classList.contains('cb-red')) }; });
  return JSON.stringify(out);
 } catch (e) { return JSON.stringify({ err: String(e) }); } })()"""
#: the fresh build's helm: Crown of Ages by name through the slot's own picker (the WORN half of the level rule)
TPL_HELM = ("(function(){ window._cbOpenPick('slot', 'head'); var hit = window._cbPickRows().filter(function(r){ return r[1] === 'Crown of Ages'; });"
            " if (hit.length !== 1){ window._cbClosePick(); return 'Crown of Ages rows: ' + hit.length; }"
            " var ok = window._cbChoose(hit[0][0]); window._cbClosePick(); return ok ? 'ok' : 'not equipped'; })()")
#: Calculations' "Requirements the level N character fails" row, read and the Equipment view put back
CALC_FAILS = ("(function(){ window._cbView('calc'); var r = null; [].forEach.call(document.querySelectorAll('#cb-win .cb-calc tr'),"
              " function(tr){ if (/Requirements the level/.test(tr.textContent)) r = tr.textContent; }); window._cbView('equip'); return r; })()")
#: a charm placed through the inventory cell's own picker: its id is the ONE database row with that name (and prefix)
TPL_PLACE = ("(function(n, x, y, pre){ window._cbOpenPick('inv', null, [x, y]); var rows = window._cbPickRows();"
             " var hit = rows.filter(function(r){ return r[1] === n && (!pre || r[0].indexOf(pre) === 0); });"
             " if (hit.length !== 1){ window._cbClosePick(); return JSON.stringify({ n: n, found: hit.length, of: rows.length }); }"
             " var ok = window._cbChoose(hit[0][0]); window._cbClosePick(); return JSON.stringify({ n: n, id: hit[0][0], ok: !!ok }); })(%s, %d, %d, %s)")

AIM = r"""(function(sel, i){ var e = document.querySelectorAll(sel)[i]; if (!e) return JSON.stringify(null);
  var r0 = e.getBoundingClientRect(); if (r0.top < 0 || r0.bottom > innerHeight || r0.left < 0 || r0.right > innerWidth)
    e.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
  var r = e.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  var at = document.elementFromPoint(x, y); return JSON.stringify({ x: x, y: y, hit: !!(at && (at === e || e.contains(at))) }); })(%s, %d)"""

MEASURE = r"""(function(){ try {
  var d = document, box = d.getElementById('cb-win'), cb = box && box.querySelector('.cb');
  if (!cb || box.hidden) return JSON.stringify({ err: 'the builder did not render (.cb absent)' });
  var ob = cb.getBoundingClientRect(), vw = innerWidth, vh = innerHeight;
  var rel = function(el){ if (!el) return null; var r = el.getBoundingClientRect(); return [r.left - ob.left, r.top - ob.top, r.width, r.height]; };
  var out = { stack: cb.classList.contains('cb-stack'), hscroll: [box.scrollWidth, box.clientWidth], cols: {}, cut: [], outside: [],
    sideways: [], collide: [], nText: 0, modal: null, covered: null, worn: box.querySelectorAll('.cb-slot.cb-has').length,
    inv: box.querySelectorAll('.cb-it').length, rolls: box.querySelectorAll('.cb-roll').length, opts: box.querySelectorAll('.cb-opt').length,
    mods: box.querySelectorAll('.cb-mod').length, addOpts: box.querySelectorAll('.cb-add-o').length,
    doll: rel(d.getElementById('cb-doll')), invRect: rel(d.getElementById('cb-inv')),
    invInMain: !!(d.getElementById('cb-inv') && d.getElementById('cb-inv').closest('.cb-main')) };
  out.cols.left = rel(box.querySelector('.cb-left')); out.cols.main = rel(box.querySelector('.cb-main')); out.cols.stats = rel(box.querySelector('.cb-stats'));
  var _sa = box.querySelector('.cb-stats'); out.statsLeftAbs = _sa ? _sa.getBoundingClientRect().left : null;  // #174 round 7: the VIEWPORT frame the modal rect is in
  /* #174 R2 — where STATS ends on the glass (at the window's scroll 0) and whether its own list scrolls */
  var _sp = box.querySelector('.cb-stats'), _sl = box.querySelector('.cb-st');
  out.statsBottom = _sp ? _sp.getBoundingClientRect().bottom : null; out.vh = vh;
  out.statsList = _sl ? [_sl.scrollHeight, _sl.clientHeight, getComputedStyle(_sl).overflowY] : null;
  var ht = box.querySelector('.cb-h-t'); out.fsTitle = ht ? parseFloat(getComputedStyle(ht).fontSize) : null;
  out.tokTitle = parseFloat(getComputedStyle(d.documentElement).getPropertyValue('--fs-title'));
  var m = d.getElementById('cb-modal');
  if (m && !m.hidden){
    var mr = m.getBoundingClientRect(); out.modal = [mr.left, mr.top, mr.width, mr.height];
    out.modalInside = mr.left >= -0.5 && mr.top >= -0.5 && mr.right <= vw + 0.5 && mr.bottom <= vh + 0.5;
    var sel = box.querySelector('.cb-slot.cb-picked');
    if (sel && !out.stack){ var sr = sel.getBoundingClientRect(), at = d.elementFromPoint(sr.left + sr.width / 2, sr.top + sr.height / 2);
      out.covered = !(at && (at === sel || sel.contains(at))); }
  }
  var roots = [cb]; if (m && !m.hidden) roots.push(m);
  roots.forEach(function(root){
    var tw = d.createTreeWalker(root, NodeFilter.SHOW_TEXT), n;
    while ((n = tw.nextNode())){
      var t = n.textContent.trim(); if (!t) continue;
      var el = n.parentElement; if (!el || el.closest('[hidden]') || el.closest('.cb-it') || el.closest('.cb-slot') || el.closest('option')) continue;
      var cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue;
      var rg = d.createRange(); rg.selectNodeContents(n);
      var L = 1e9, T = 1e9, R = -1e9, B = -1e9;
      [].forEach.call(rg.getClientRects(), function(r){ if (r.width < 0.5 && r.height < 0.5) return;
        L = Math.min(L, r.left); T = Math.min(T, r.top); R = Math.max(R, r.right); B = Math.max(B, r.bottom); });
      if (L > R) continue;
      out.nText++;
      var scrolled = false;
      for (var a = el; a && a !== box; a = a.parentElement){
        var s = getComputedStyle(a); if (s.overflowX === 'visible' && s.overflowY === 'visible') continue;
        var ar = a.getBoundingClientRect(), cl = ar.left + a.clientLeft, ct = ar.top + a.clientTop, cr = cl + a.clientWidth, cbt = ct + a.clientHeight;
        var hx = (L < cl - 0.5 || R > cr + 0.5), hy = (T < ct - 0.5 || B > cbt + 0.5);
        var hid = function(o){ return o === 'hidden' || o === 'clip'; };
        if ((hx && hid(s.overflowX)) || (hy && hid(s.overflowY)))
          out.cut.push(String(a.className).slice(0, 30) + ' cuts "' + t.slice(0, 48) + '"');
        scrolled = !hid(s.overflowX) || !hid(s.overflowY);
        break;
      }
      var p = el.closest('.cb-p') || el.closest('.cb-modal');
      if (p && !scrolled){ var pr = p.getBoundingClientRect();
        if (B > pr.bottom + 0.5 || R > pr.right + 0.5 || L < pr.left - 0.5) out.outside.push('"' + t.slice(0, 40) + '" outside ' + String(p.className).slice(0, 24)); }
    }
    [].forEach.call(root.querySelectorAll('button,select,input,textarea,.cb-it'), function(e){
      if (e.closest('[hidden]')) return;
      var r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return;
      for (var a = e.parentElement; a && a !== box; a = a.parentElement){
        var s = getComputedStyle(a); if (s.overflowX === 'visible' && s.overflowY === 'visible') continue;
        var hid = function(o){ return o === 'hidden' || o === 'clip'; };
        var ar = a.getBoundingClientRect(), cl = ar.left + a.clientLeft, ct = ar.top + a.clientTop, cr = cl + a.clientWidth, cbt = ct + a.clientHeight;
        var dx = Math.max(cl - r.left, r.right - cr), dy = Math.max(ct - r.top, r.bottom - cbt);
        if ((dx > 0.5 && hid(s.overflowX)) || (dy > 0.5 && hid(s.overflowY)))
          out.cut.push(String(a.className).slice(0, 30) + ' cuts the control ' + String(e.className || e.tagName).slice(0, 30) + ' by ' + Math.max(dx, dy).toFixed(1) + 'px');
        break;
      }
    });
    [].forEach.call(root.querySelectorAll('*'), function(e){ var s = getComputedStyle(e);
      if ((s.overflowX === 'auto' || s.overflowX === 'scroll') && e.scrollWidth > e.clientWidth + 1)
        out.sideways.push(String(e.className || e.tagName).slice(0, 30) + ' ' + e.scrollWidth + '/' + e.clientWidth); });
  });
  [].forEach.call(box.querySelectorAll('.cb-h'), function(h){
    var c = h.querySelector('.cb-h-r'), t = h.querySelector('.cb-h-t'); if (!c || !c.firstElementChild || !t) return;
    var rg = d.createRange(); rg.selectNodeContents(t); var tr = rg.getBoundingClientRect(), cr = c.getBoundingClientRect();
    if (tr.right > cr.left + 0.5 && tr.bottom > cr.top && tr.top < cr.bottom) out.collide.push('"' + t.textContent.trim() + '" runs under its control'); });
  return JSON.stringify(out);
 } catch (e) { return JSON.stringify({ err: String(e) }); } })()"""

_CACHE = {}


def _press(t, sel, i=0):
    a = json.loads(t.ev(AIM % (json.dumps(sel), i)))
    if not a:
        return "no %s[%d] on the page" % (sel, i)
    time.sleep(0.15)
    a = json.loads(t.ev(AIM % (json.dumps(sel), i)))
    if not a["hit"]:
        return "the centre of %s[%d] is covered by another element" % (sel, i)
    for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
        t.send("Input.dispatchMouseEvent", type=kind, x=a["x"], y=a["y"], button="none" if kind == "mouseMoved" else "left",
               buttons=1 if kind == "mousePressed" else 0, clickCount=0 if kind == "mouseMoved" else 1)
    time.sleep(0.25)
    return None


def _drag(t, sel, i, sel2, j):
    a = json.loads(t.ev(AIM % (json.dumps(sel), i)))
    b = json.loads(t.ev(AIM % (json.dumps(sel2), j)))
    if not a or not b or not a["hit"]:
        return "cannot aim the drag: %s -> %s" % (a, b)
    t.send("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"], y=a["y"], button="none", buttons=0)
    t.send("Input.dispatchMouseEvent", type="mousePressed", x=a["x"], y=a["y"], button="left", buttons=1, clickCount=1)
    for k in range(1, 9):
        t.send("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"] + (b["x"] - a["x"]) * k / 8.0,
               y=a["y"] + (b["y"] - a["y"]) * k / 8.0, button="left", buttons=1)
        time.sleep(0.03)
    t.send("Input.dispatchMouseEvent", type="mouseReleased", x=b["x"], y=b["y"], button="left", buttons=0, clickCount=1)
    time.sleep(0.3)
    return None


def _type(t, text):
    for ch in text:
        t.send("Input.dispatchKeyEvent", type="keyDown", text=ch, key=ch, unmodifiedText=ch)
        t.send("Input.dispatchKeyEvent", type="keyUp", key=ch)


def _key(t, k, code):
    t.send("Input.dispatchKeyEvent", type="keyDown", key=k, code=k, windowsVirtualKeyCode=code, nativeVirtualKeyCode=code,
           **({"text": "\r"} if k == "Enter" else {}))
    t.send("Input.dispatchKeyEvent", type="keyUp", key=k, code=k, windowsVirtualKeyCode=code, nativeVirtualKeyCode=code)
    time.sleep(0.2)


def _row(t, name):
    return t.ev("(function(n){ var o = document.querySelectorAll('#cb-list .cb-opt'); for (var i = 0; i < o.length; i++) "
                "if (o[i].textContent === n) return i; return -1; })(%s)" % json.dumps(name))


LIST = r"""(function(){ var l = document.getElementById('cb-list'); if (!l) return 'null';
  var o = l.querySelectorAll('.cb-opt'), last = o[o.length - 1]; if (!last) return 'null';
  var lr = l.getBoundingClientRect(), r = last.getBoundingClientRect();
  var cx = (Math.max(lr.left, 0) + Math.min(lr.right, innerWidth)) / 2, cy = (Math.max(lr.top, 0) + Math.min(lr.bottom, innerHeight)) / 2;
  var hit = document.elementFromPoint(cx, cy), y = r.top + r.height / 2, at = (y > 0 && y < innerHeight) ? document.elementFromPoint(r.left + Math.min(20, r.width / 2), y) : null;
  return JSON.stringify({ rows: o.length, scroll: [l.scrollTop, l.scrollHeight, l.clientHeight], listH: lr.height, cx: cx, cy: cy,
    aim: !!(hit && l.contains(hit)), lastTop: r.top, lastSeen: !!(at && (at === last || last.contains(at))), name: last.textContent }); })()"""
#: #174 v-B3 fix round - the open ADD MOD list against the room of the Edit tab it sits in (#cb-ed, the modal's scroller)
FIT = r"""(function(){ var l = document.getElementById('cb-add-list'), ed = document.getElementById('cb-ed');
  if (!l || !ed) return 'null';
  var lr = l.getBoundingClientRect(), er = ed.getBoundingClientRect(), o = l.querySelectorAll('.cb-add-o'), seen = 0;
  [].forEach.call(o, function(x){ var r = x.getBoundingClientRect(); if (r.top >= lr.top - 0.5 && r.bottom <= lr.bottom + 0.5 && r.top >= er.top - 0.5 && r.bottom <= er.bottom + 0.5) seen++; });
  return JSON.stringify({ top: lr.top, bottom: lr.bottom, ch: l.clientHeight, sh: l.scrollHeight, edTop: er.top, edBottom: er.bottom, opts: o.length, seen: seen }); })()"""
#: #174 v-B3 fix round - what the keyboard left: focus, the active option (aria-activedescendant), how it is painted
COMBO = r"""(function(){ var q = document.getElementById('cb-add-q'), ae = document.activeElement, id = q && q.getAttribute('aria-activedescendant');
  var a = id ? document.getElementById(id) : null, acts = document.querySelectorAll('#cb-add-list .cb-add-o.cb-act');
  var e = null; try { var b = JSON.parse(window.LSR.getItem('d2r_charBuilds') || '{}'), k = Object.keys(b)[0]; e = b[k].sets[0].slots.head; } catch (x) {}
  return JSON.stringify({ focus: ae ? ae.id : null, role: q ? q.getAttribute('role') : null, active: id, activeId: a ? a.getAttribute('data-id') : null,
    painted: a ? getComputedStyle(a).backgroundColor : null, acts: acts.length, second: (document.querySelectorAll('#cb-add-list .cb-add-o')[1] || {}).id || null,
    stored: e && e.affixes ? e.affixes.map(function(x){ return x.id; }) : null }); })()"""
HOVER_READ = r"""(function(sel){ var e = document.querySelector(sel); if (!e) return 'null'; var cs = getComputedStyle(e);
  return JSON.stringify({ color: cs.color, bg: cs.backgroundColor, hover: e.matches(':hover'), text: e.textContent.trim() }); })(%s)"""


#: #174 round 2 (the Grok seat on v3509) - how many options are PAINTED, which one is active, which one the pointer is on
LIT = r"""(function(){ var os = document.querySelectorAll('#cb-add-list .cb-add-o'), lit = [], q = document.getElementById('cb-add-q');
  [].forEach.call(os, function(o, i){ var bg = getComputedStyle(o).backgroundColor; if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') lit.push(i); });
  var under = -1; [].forEach.call(os, function(o, i){ if (o.matches(':hover')) under = i; });
  var id = q && q.getAttribute('aria-activedescendant'), act = -1; [].forEach.call(os, function(o, i){ if (o.id === id) act = i; });
  return JSON.stringify({ n: os.length, lit: lit, under: under, active: act }); })()"""
#: #174 round 2 - every stat label that wraps: the left edge of its first line and of its second
INDENT = r"""(function(){ var out = [];
  [].forEach.call(document.querySelectorAll('#cb-win .cb-st-r:not([hidden]) .cb-sl'), function(l){
    var rg = document.createRange(); rg.selectNodeContents(l);
    var lines = {}; [].forEach.call(rg.getClientRects(), function(x){ if (x.width < 0.5) return; var k = Math.round(x.top); if (!(k in lines) || x.left < lines[k]) lines[k] = x.left; });
    var ks = Object.keys(lines).map(Number).sort(function(a, b){ return a - b; });
    if (ks.length > 1) out.push({ text: l.textContent.trim(), first: lines[ks[0]], next: lines[ks[1]] }); });
  return JSON.stringify(out); })()"""


#: #174 round 3 - rows whose value sits BELOW its label's first line, and label text running under its value
DROP = r"""(function(){ var out = [];
  [].forEach.call(document.querySelectorAll('#cb-win .cb-st-r:not([hidden])'), function(r){
    var l = r.querySelector('.cb-sl'), v = r.querySelector('.cb-sv'); if (!l || !v) return;
    var rg = document.createRange(); rg.selectNodeContents(l);
    var rs = [].slice.call(rg.getClientRects()).filter(function(x){ return x.width > 0.5; });
    if (rs.length && v.getBoundingClientRect().top > rs[0].bottom - 1) out.push(l.textContent.trim()); });
  return JSON.stringify(out); })()"""
OVER = r"""(function(){ var bad = [];
  [].forEach.call(document.querySelectorAll('#cb-win .cb-st-r:not([hidden])'), function(r){
    var l = r.querySelector('.cb-sl'), v = r.querySelector('.cb-sv'); if (!l || !v) return;
    var rg = document.createRange(); rg.selectNodeContents(l); var vr = v.getBoundingClientRect();
    [].forEach.call(rg.getClientRects(), function(x){
      if (x.width > 0.5 && x.bottom > vr.top + 1 && x.top < vr.bottom - 1 && x.right > vr.left + 0.5) bad.push(l.textContent.trim()); }); });
  return JSON.stringify(bad); })()"""
#: the same page with the hanging indent taken away - what v-B2's rule gave before round 2
FLUSH_ON = ("(function(){ var s = document.createElement('style'); s.id = 'law-flush'; s.textContent = "
            "'.cb-st-r .cb-sl{padding-left:0 !important;text-indent:0 !important;margin-right:0 !important}';"
            " document.head.appendChild(s); return 1; })()")
FLUSH_OFF = "(function(){ var s = document.getElementById('law-flush'); if (s) s.remove(); return 1; })()"
#: #29(a) 2026-09-28 - ONE row wider than the rows beside it: Fire carries a rolled range that crosses zero (the widest shape a
#: resistance prints) while Cold / Lightning / Poison keep what the build gives them. Measured on v3521: that row alone put its
#: value on a line of its own at 960-1180. Returns the value text it set, or null when the Fire row is not drawn
WIDEN = r"""(function(){ var v = document.querySelector('#cb-win .cb-st-r[data-k="fire resistance"] .cb-sv'); if (!v) return null;
  var b = v.querySelector('b'); if (!b) { b = document.createElement('b'); v.insertBefore(b, v.firstChild); }
  v.className = 'cb-sv cb-sv-RANGE'; b.textContent = '−50 to −40%'; var i = v.querySelector('i'); if (i) i.textContent = 'RANGE';
  return v.textContent; })()"""
#: #29(a) - a part of a value (the number, its RANGE chip, its cap) that lies outside its own row, or past STATS' right edge
SPILL = r"""(function(){ var out = [], st = document.querySelector('#cb-win .cb-st'), sr = st && st.getBoundingClientRect();
  [].forEach.call(document.querySelectorAll('#cb-win .cb-st-r:not([hidden])'), function(r){
    var l = r.querySelector('.cb-sl'), v = r.querySelector('.cb-sv'); if (!l || !v) return; var rr = r.getBoundingClientRect();
    [].forEach.call(v.children, function(c){ var cr = c.getBoundingClientRect(); if (cr.width < 0.5) return;
      if (cr.right > rr.right + 0.5 || cr.left < rr.left - 0.5 || cr.bottom > rr.bottom + 0.5 || cr.top < rr.top - 0.5 || (sr && cr.right > sr.right + 0.5))
        out.push(l.textContent.trim() + ': ' + c.textContent); }); });
  return JSON.stringify(out); })()"""
#: the band where the stats column is tight enough for a label to wrap (measured 2026-09-26: every regression was 900-1240)
SWEEP = range(900, 1401, 20)
#: #42 - the sweep's own viewports (its height follows the width, as it always did), so a red-proof can name one
SWEEP_AT = tuple((w, 1300 if w >= 1280 else 800) for w in SWEEP)
#: #42 - the ONE-viewport steps: the keyboard/pointer/hover/tile passes at 2000, the wrapped-label indent at 1280x800
AT_2000, AT_INDENT = (2000, 1300), (1280, 800)
#: every viewport this law measures at - what TV_LAW_WIDTHS may name
VIEWPORTS = tuple(sorted(set(WIDTHS) | set(MOD_WIDTHS) | set(TPL_WIDTHS) | set(SWEEP_AT) | {AT_2000, AT_INDENT}))
#: #42 - a PUSH-TIME red-proof restricts every width loop to the viewports it declares (heart2 --push --prove hands them
#: over as TV_LAW_WIDTHS). None = every width, exactly as before; run_gates and CI never set it. A case whose viewports
#: are all outside the set is a declared SKIP; the fixture's own steps (the entry, the equip, the fresh build) always run.
_ONLY = LW.only()
_W = lambda seq: LW.pick(seq, _ONLY)  # noqa: E731

#: #29(d) round 9 - the Edit window's body: how much of it lies EMPTY under its last line, whether it scrolls, and how much
#: of the glass is free under the window
EDFIT = r"""(function(){ var m = document.getElementById('cb-modal'); if (!m || m.hidden) return JSON.stringify({ err: 'no modal open' });
  var ed = m.querySelector('.cb-ed'); if (!ed) return JSON.stringify({ err: 'no Edit body (.cb-ed) in the modal' });
  var mr = m.getBoundingClientRect(), er = ed.getBoundingClientRect(), cs = getComputedStyle(ed), lc = ed.lastElementChild;
  var bodyBottom = er.top + ed.clientTop + ed.clientHeight;
  var inkBottom = lc ? lc.getBoundingClientRect().bottom + (parseFloat(getComputedStyle(lc).marginBottom) || 0) + (parseFloat(cs.paddingBottom) || 0) : er.top;
  /* a number box's range hint (placeholder) against the room its box gives it, less the spin arrows */
  var ph = [].map.call(m.querySelectorAll('input[type=number][placeholder]'), function(i){ var s = getComputedStyle(i), c = document.createElement('canvas').getContext('2d');
    c.font = s.fontStyle + ' ' + s.fontWeight + ' ' + s.fontSize + ' ' + s.fontFamily;
    return { id: i.id, ph: i.placeholder, text: c.measureText(i.placeholder).width, room: i.clientWidth - (parseFloat(s.paddingLeft) || 0) - (parseFloat(s.paddingRight) || 0) }; });
  return JSON.stringify({ modal: [mr.left, mr.top, mr.width, mr.height], empty: bodyBottom - inkBottom, sh: ed.scrollHeight, ch: ed.clientHeight,
    free: innerHeight - 8 - mr.bottom, sheet: m.classList.contains('cb-sheet'), n: ed.children.length, ph: ph }); })()"""
#: #29(d) round 9 - the builder's own tab row while a modal is open: overlapped or not, and each tab's centre hit-tested
TABS = r"""(function(){ var m = document.getElementById('cb-modal'), tb = document.querySelector('#cb-win .cb-ctabs');
  if (!m || m.hidden) return JSON.stringify({ modal: false });
  if (!tb) return JSON.stringify({ modal: true, err: 'the tab row (.cb-ctabs) is not drawn' });
  var mr = m.getBoundingClientRect(), tr = tb.getBoundingClientRect(), vh = innerHeight;
  var onScreen = tr.height > 0 && tr.bottom > 0 && tr.top < vh;
  var over = mr.left < tr.right && mr.right > tr.left && mr.top < tr.bottom && mr.bottom > tr.top;
  var hit = [].map.call(tb.querySelectorAll('.cb-ctab'), function(b){ var r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
    var at = (y >= 0 && y < vh) ? document.elementFromPoint(x, y) : null; return { tab: b.textContent.trim(), seen: !!(at && (at === b || b.contains(at))) }; });
  return JSON.stringify({ modal: true, onScreen: onScreen, room: vh - tr.bottom, over: over, hit: hit, tabs: [tr.left, tr.top, tr.width, tr.height],
    at: [mr.left, mr.top, mr.width, mr.height] }); })()"""
#: REG-1376 round 2 - every capped STATS row: its label's lines with the cap chip, and with the chip taken away (a style that
#: hides it, removed in the same evaluate); the chip's own lines, and whether it lies inside its row
CAPS = r"""(function(){ var rows = [].slice.call(document.querySelectorAll('#cb-win .cb-st-r:not([hidden])')).filter(function(r){ return !!r.querySelector('.cb-cap'); });
  var lines = function(el){ var g = document.createRange(); g.selectNodeContents(el); var t = [];
    [].forEach.call(g.getClientRects(), function(c){ if (c.width > 0.5 && !t.some(function(x){ return Math.abs(x - c.top) < 3; })) t.push(c.top); });
    return t.length; };
  var out = rows.map(function(r){ var c = r.querySelector('.cb-cap'), rr = r.getBoundingClientRect(), cr = c.getBoundingClientRect();
    return { k: r.querySelector('.cb-sl').textContent.trim(), n: lines(r.querySelector('.cb-sl')), cap: c.textContent, capLines: lines(c),
             capIn: cr.left >= rr.left - 0.5 && cr.right <= rr.right + 0.5 && cr.top >= rr.top - 0.5 && cr.bottom <= rr.bottom + 0.5 }; });
  var s = document.createElement('style'); s.textContent = '#cb-win .cb-st-r .cb-cap{display:none !important}'; document.body.appendChild(s);
  try { rows.forEach(function(r, i){ out[i].bare = lines(r.querySelector('.cb-sl')); }); } finally { s.parentNode.removeChild(s); }
  return JSON.stringify(out); })()"""
#: REG-1379 round 2 - the WINDOW against what it holds, STATS against the columns beside it, and the natural heights of
#: STRENGTHS AND WEAKNESSES and NOTES: their own content (or their min-height floors) with every stretch taken away,
#: measured by sizing each to max-content in place
TIGHT = r"""(function(){ var w = document.getElementById('cb-win'), cb = w && w.querySelector('.cb'); if (!cb) return JSON.stringify({ err: 'no builder' });
  var q = function(s){ return w.querySelector(s); }, bot = function(e){ return e ? e.getBoundingClientRect().bottom : null; };
  var natural = function(e){ if (!e) return null; var s = e.style;
    s.setProperty('height', 'max-content', 'important'); s.setProperty('flex', 'none', 'important'); s.setProperty('align-self', 'flex-start', 'important');
    var h = e.getBoundingClientRect().height; s.removeProperty('height'); s.removeProperty('flex'); s.removeProperty('align-self'); return h; };
  var wr = w.getBoundingClientRect(), sw = q('.cb-left > :last-child'), nt = q('.cb-notes');
  return JSON.stringify({ stack: cb.classList.contains('cb-stack'), win: [wr.top, wr.bottom], cb: bot(cb), vh: innerHeight, sh: w.scrollHeight,
    ch: w.clientHeight, pb: parseFloat(getComputedStyle(w).paddingBottom) || 0, left: bot(q('.cb-left')), notes: bot(nt), stats: bot(q('.cb-stats')),
    sw: sw ? [sw.getBoundingClientRect().height, natural(sw), String(sw.className)] : null,
    nt: nt ? [nt.getBoundingClientRect().height, natural(nt)] : null }); })()"""
EDIT_STATES = ("edit", "mods", "gcmods")
BAND_TOL = 1.5
EMPTY_MAX = 12.0


def _point_at(t, sel, i):
    """the pointer comes to rest on the i-th match (two real moves) - no click"""
    a = json.loads(t.ev(AIM % (json.dumps(sel), i)))
    if not a or not a["hit"]:
        return "cannot aim at %s[%d]: %s" % (sel, i, a)
    for dx in (0, 1):
        t.send("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"] + dx, y=a["y"], button="none")
        time.sleep(0.15)
    return None


def _wheel_list(t):
    """a REAL wheel over the picker's list: 40 notches, then is its last row on screen?"""
    b = json.loads(t.ev(LIST))
    if not b or not b["aim"]:
        return {"err": "the list is not under the pointer: %s" % b}
    for _ in range(40):
        t.send("Input.dispatchMouseEvent", type="mouseWheel", x=b["cx"], y=b["cy"], deltaX=0, deltaY=400)
        time.sleep(0.02)
    time.sleep(0.5)
    return {"before": b, "after": json.loads(t.ev(LIST))}


def _hover(t, sel):
    """the pointer comes to rest on a control (two real moves, so the hover state is the page's own)"""
    a = json.loads(t.ev(AIM % (json.dumps(sel), 0)))
    if not a or not a["hit"]:
        return {"err": "cannot aim at %s: %s" % (sel, a)}
    for dx in (0, 1):
        t.send("Input.dispatchMouseEvent", type="mouseMoved", x=a["x"] + dx, y=a["y"], button="none")
        time.sleep(0.15)
    return json.loads(t.ev(HOVER_READ % json.dumps(sel)))


def _set_size(t, w, h):
    t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=(w < 500))
    time.sleep(0.3)


def _measure():
    if "r" in _CACHE:
        return _CACHE["r"]
    RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
    res = {"input": []}
    try:
        t = RC._Tab("about:blank")
        t.send("Page.enable")
        t.send("Runtime.enable")
        _set_size(t, 2000, 1300)
        t.send("Page.navigate", url="file://" + os.path.join(ROOT, "bible.html"))
        for _ in range(200):
            time.sleep(0.25)
            try:
                if t.ev("document.readyState==='complete' && !!window.openCharBuilder && !!window.LSR") is True:
                    break
            except Exception:
                pass
        else:
            raise AssertionError("bible.html never exposed openCharBuilder in 50s — UNKNOWN, not passing")
        time.sleep(0.6)
        # ⚠ 2026-09-26 — MEASURE AFTER THE FONTS. The page pulls Cinzel / Playfair / Inter from Google Fonts; on CI they
        # arrive over the network at a variable time, and a row measured before its font lands reflows a few px later.
        # MEASURED: the mule law read the stash-in-front EQUIPMENT panel 6 px low on one CI run of v3513 and exact on the
        # re-run of the same commit. Bounded (15 s); the status measured under is recorded, never assumed.
        for _ in range(60):
            try:
                if t.ev("document.fonts.status") == "loaded":
                    break
            except Exception:
                pass
            time.sleep(0.25)
        res["fonts"] = t.ev("document.fonts.status")
        # THE ENTRY, BY REAL INPUT: the Tools tab, then the Character Builder card
        res["input"].append(_press(t, '.tab[data-tab="tools"]'))
        time.sleep(0.8)
        res["input"].append(_press(t, "#char-builder-card .boss-header"))
        time.sleep(0.6)
        res["opened"] = t.ev("(function(){ var w = document.getElementById('cb-win'); return !!w && !w.hidden; })()")
        # plain, at every width
        for (w, h) in _W(WIDTHS):
            _set_size(t, w, h)
            t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); return 1; })()")
            time.sleep(0.35)
            res["plain %dx%d" % (w, h)] = json.loads(t.ev(MEASURE))
            res["caps plain %dx%d" % (w, h)] = json.loads(t.ev(CAPS))   # REG-1376 round 2
            res["tight plain %dx%d" % (w, h)] = json.loads(t.ev(TIGHT))  # REG-1379 round 2
            res["tpl plain %dx%d" % (w, h)] = json.loads(t.ev(TEMPLATE))
        # equip by real input at 2000: the helm slot, the search box, the row; a roll typed; a charm dropped and dragged
        _set_size(t, 2000, 1300)
        t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); return 1; })()")
        time.sleep(0.4)
        res["input"].append(_press(t, '#cb-win .cb-slot[data-slot="head"]'))
        res["input"].append(_press(t, "#cb-pick-q"))
        _type(t, "crown of ages")
        time.sleep(0.3)
        i = _row(t, "Crown of Ages")
        res["input"].append(("Crown of Ages was not listed") if i is None or i < 0 else _press(t, "#cb-list .cb-opt", i))
        res["input"].append(_press(t, "#cb-lines .cb-roll", 1))
        _type(t, "28")
        _key(t, "Enter", 13)
        _key(t, "Escape", 27)
        res["input"].append(_press(t, "#cb-inv .cb-cell", 0))
        i = _row(t, "Annihilus")
        res["input"].append(("Annihilus was not listed") if i is None or i < 0 else _press(t, "#cb-list .cb-opt", i))
        _key(t, "Escape", 27)
        res["input"].append(_drag(t, "#cb-inv .cb-it", 0, "#cb-inv .cb-cell", 25))
        res["store"] = t.ev("(function(){ var b = JSON.parse(window.LSR.getItem('d2r_charBuilds') || '{}'), k = Object.keys(b)[0];"
                            " if (!k) return null; var s = b[k].sets[0]; return JSON.stringify({ head: s.slots.head && [s.slots.head.name, s.slots.head.rolls],"
                            " inv: s.inv.map(function(e){ return [e.name, e.x, e.y]; }) }); })()")
        for (w, h) in _W(WIDTHS):
            _set_size(t, w, h)
            for state in ("worn", "picker", "edit", "stash", "invpick"):
                js = {"worn": "", "picker": "window._cbOpenPick('slot','head'); window._cbPickTab('select');",
                      "edit": "window._cbOpenPick('slot','head');", "stash": "window._cbOpenStash();",
                      "invpick": "window._cbOpenPick('inv', null, [0, 0]);"}[state]
                t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); %s return 1; })()" % js)
                time.sleep(0.35)
                res["%s %dx%d" % (state, w, h)] = json.loads(t.ev(MEASURE))
                if state == "worn":
                    res["tpl worn %dx%d" % (w, h)] = json.loads(t.ev(TEMPLATE))
                    res["caps worn %dx%d" % (w, h)] = json.loads(t.ev(CAPS))    # REG-1376 round 2
                    res["tight worn %dx%d" % (w, h)] = json.loads(t.ev(TIGHT))  # REG-1379 round 2
                else:
                    res["tabs %s %dx%d" % (state, w, h)] = json.loads(t.ev(TABS))       # #29(d) round 9
                if state == "edit":
                    res["edfit %s %dx%d" % (state, w, h)] = json.loads(t.ev(EDFIT))
        # #174 v-B2 fix round - the picker's list, by a real wheel, at 375 and 2000
        for (w, h) in _W(WHEEL_WIDTHS):
            _set_size(t, w, h)
            for slot in ("rarm", "feet"):
                t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); return 1; })()")
                time.sleep(0.35)
                res["input"].append(_press(t, '#cb-win .cb-slot[data-slot="%s"]' % slot))
                time.sleep(0.3)
                res["wheel %s %dx%d" % (slot, w, h)] = _wheel_list(t)
        # #174 v-B3 - the Edit tab of a BASE with picked mods (a rare Diadem with four, a magic Grand Charm with two), and
        # its ADD MOD list open, at 2000 / 1280 / 375 - through the builder's own entry points (Choose -> Quality -> Add)
        for (w, h) in _W(MOD_WIDTHS):
            _set_size(t, w, h)
            for state in MOD_STATES:
                t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); %s return 1; })()" % MOD_JS[state])
                time.sleep(0.35)
                res["%s %dx%d" % (state, w, h)] = json.loads(t.ev(MEASURE))
                res["tabs %s %dx%d" % (state, w, h)] = json.loads(t.ev(TABS))           # #29(d) round 9
                if state in EDIT_STATES:
                    res["edfit %s %dx%d" % (state, w, h)] = json.loads(t.ev(EDFIT))
                if state.endswith("addmod"):
                    res["fit %s %dx%d" % (state, w, h)] = json.loads(t.ev(FIT))
                if state.startswith("gc"):
                    # #174 round 7 - the charm's Edit tile draws its in-game art, not its name in a box
                    res["gcart %s %dx%d" % (state, w, h)] = json.loads(t.ev(
                        "(function(){ var m = document.getElementById('cb-modal'); return JSON.stringify({ img: !!(m && m.querySelector('.d2art-wrap img')),"
                        " failed: !!(m && m.querySelector('.d2art-failed')) }); })()"))
                    t.ev("(function(){ window._cbUnequip(); window._cbClosePick(); return 1; })()")
        # #42 - one viewport: measured unless a push-time proof restricted the run elsewhere
        if LW.at(AT_2000, _ONLY):
            # #174 v-B3 fix round - ADD MOD by the KEYBOARD, real input at 2000: a rare Diadem with two prefixes, the search box
            # pressed, "res" typed, ArrowDown, then Enter - focus must stay in the box and the painted option be what Enter adds
            _set_size(t, 2000, 1300)
            t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); window._cbOpenPick('slot','head'); window._cbChoose('b:ci3');"
                 " window._cbQuality('rare'); ['p712','s175'].forEach(function(i){ window._cbAddMod(i); }); window._cbModOpen(true); return 1; })()")
            time.sleep(0.35)
            res["input"].append(_press(t, "#cb-add-q"))
            _type(t, "res")
            time.sleep(0.3)
            combo = {"typed": json.loads(t.ev(COMBO))}
            _key(t, "ArrowDown", 40)
            combo["down"] = json.loads(t.ev(COMBO))
            _key(t, "Enter", 13)
            time.sleep(0.2)
            combo["enter"] = json.loads(t.ev(COMBO))
            res["combo"] = combo
            # #174 round 2 (the Grok seat on v3509) - the POINTER and the keys light ONE row between them: the pointer comes to
            # rest on the 4th option (real moves, no click), then a real ArrowDown with the pointer still there
            t.ev("(function(){ window._cbModOpen(true); return 1; })()")
            time.sleep(0.3)
            res["input"].append(_point_at(t, "#cb-add-list .cb-add-o", 3))
            lit = {"pointer": json.loads(t.ev(LIT))}
            _key(t, "ArrowDown", 40)
            time.sleep(0.2)
            lit["down"] = json.loads(t.ev(LIT))
            res["lit"] = lit
            t.ev("(function(){ window._cbClosePick(); return 1; })()")
        # #174 round 2 - a wrapped stat label's second line is set in (a hanging indent), at 1280 where several wrap
        # ⚠ #42 - THE DIADEM IS SET WHATEVER THE RESTRICTION, ONLY THE MEASUREMENT IS SKIPPED: the sweep below reads STATS
        # with THIS helm on the doll, so a push-time run at one sweep width must reach it in the same state as the full run
        # (skipped, the doll would still wear what the steps before it left - Crown of Ages when no Edit width is measured -
        # and the sweep would read a different STATS panel from the verdict of record's)
        _set_size(t, 1280, 800)
        t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); %s window._cbClosePick(); return 1; })()" % _DIADEM)
        time.sleep(0.35)
        if LW.at(AT_INDENT, _ONLY):
            res["indent"] = json.loads(t.ev(INDENT))
        # #174 round 3 (the Grok seat on v3510) - v-B2's rule at EVERY width of the tight band, not only at the fixed
        # widths above: round 2's indent dropped a value at 900 / 960 / 980 / 1200-1240, all BETWEEN them
        sweep = []
        for (w, h) in _W(SWEEP_AT):
            _set_size(t, w, h)
            time.sleep(0.2)
            real, over = json.loads(t.ev(DROP)), json.loads(t.ev(OVER))
            t.ev(FLUSH_ON)
            try:                          # the #231 eye on v3512: the injected style never outlives its measurement
                time.sleep(0.05)
                flush = json.loads(t.ev(DROP))
            finally:
                t.ev(FLUSH_OFF)
            spill = json.loads(t.ev(SPILL))
            # #29(a) - the same width with ONE row widened; the page is drawn again afterwards, so the widening never
            # reaches the next width's measurement
            widened = t.ev(WIDEN)
            try:
                time.sleep(0.05)
                wide, wspill, wover = json.loads(t.ev(DROP)), json.loads(t.ev(SPILL)), json.loads(t.ev(OVER))
            finally:
                t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); window._cbClosePick(); return 1; })()")
                time.sleep(0.3)
            sweep.append({"w": w, "extra": sorted(set(real) - set(flush)), "over": over, "rows": len(real) + 0,
                          "real": real, "spill": spill, "widened": widened, "wide": wide, "wspill": wspill, "wover": wover})
        res["sweep"] = sweep
        # #42 - one viewport, as above
        if LW.at(AT_2000, _ONLY):
            # an ACTIVE button under the pointer, pressed by real input first where it is a toggle
            _set_size(t, 2000, 1300)
            t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); return 1; })()")
            time.sleep(0.35)
            hv = {}
            hv["set"] = _hover(t, "#cb-win .cb-settabs .cb-btn.cb-on")
            hv["quests"] = _hover(t, "#cb-win .cb-stats .cb-h-r .cb-btn.cb-on")
            res["input"].append(_press(t, '#cb-win .cb-slot[data-slot="glov"]'))
            res["input"].append(_press(t, "#cb-modal .cb-srow .cb-btn"))
            hv["filters"] = _hover(t, "#cb-modal .cb-srow .cb-btn.cb-on")
            _key(t, "Escape", 27)
            _key(t, "Escape", 27)
            t.ev("(function(){ window.openCharBuilder(); window._cbOpenNew(); return 1; })()")
            time.sleep(0.3)
            res["input"].append(_press(t, "#cb-modal .cb-new-cls .cb-btn", 1))
            hv["class"] = _hover(t, "#cb-modal .cb-new-cls .cb-btn.cb-on")
            res["hover"] = hv
        # #174 v-B4 - LAST, because it makes a new build the selected one: a fresh build, three charms placed through the
        # inventory cell's own picker, the template measured at the builder's five sizes
        _set_size(t, 2000, 1300)
        res["tpl new"] = t.ev(TPL_NEW)
        time.sleep(0.4)
        res["tpl before"] = json.loads(t.ev(TEMPLATE))
        res["tpl placed"] = [json.loads(t.ev(TPL_PLACE % (json.dumps(n), x, y, json.dumps(pre)))) for (n, x, y, pre) in TPL_CHARMS]
        time.sleep(0.3)
        for (w, h) in _W(TPL_WIDTHS):
            _set_size(t, w, h)
            t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); return 1; })()")
            time.sleep(0.4)
            res["tpl charms %dx%d" % (w, h)] = json.loads(t.ev(TEMPLATE))
        # #42 - one viewport, as above
        if LW.at(AT_2000, _ONLY):
            # #174 v-B4 fix round - the tiles' STATE at 2000: at the build's own level; one tile pressed by REAL input (Edit
            # opens on it); then at Gheed's Fortune's Required Level (read from its tooltip) and one lower by a REAL press of
            # the level's down arrow
            _set_size(t, 2000, 1300)
            t.ev("(function(){ window.closeCharBuilder(); window.openCharBuilder(); return 1; })()")
            time.sleep(0.4)
            lv = {"helm": t.ev(TPL_HELM)}
            time.sleep(0.4)
            lv["max"] = json.loads(t.ev(TILES))
            names = [x.get("name") for x in lv["max"].get("tiles", [])]
            gi = names.index("Grand Charm") if "Grand Charm" in names else -1
            lv["press"] = _press(t, "#cb-inv .cb-it", gi) if gi >= 0 else "no Grand Charm tile: %s" % names
            time.sleep(0.3)
            lv["sel"] = json.loads(t.ev(TILES))
            _key(t, "Escape", 27)
            need = dict((x.get("name"), x.get("need")) for x in lv["max"].get("tiles", []))
            mid = need.get("Gheed's Fortune") or 0
            if mid > 1:
                t.ev("(function(){ window._cbSetField('level', %d); return 1; })()" % mid)
                time.sleep(0.4)
                lv["mid"] = json.loads(t.ev(TILES))
                lv["midCalc"] = t.ev(CALC_FAILS)
                time.sleep(0.3)
                lv["down"] = _press(t, '#cb-win .cb-step button[aria-label="level down"]')
                time.sleep(0.4)
                lv["low"] = json.loads(t.ev(TILES))
                lv["lowCalc"] = t.ev(CALC_FAILS)
            res["tiles"] = lv
        res["errors"] = list(getattr(t, "page_errors", []) or [])
        try:
            t.close()
        except Exception:
            pass
    finally:
        RC._chrome_down()
    _CACHE["r"] = res
    return res


def _states():
    r = _measure()
    return [("%s %dx%d" % (s, w, h), r["%s %dx%d" % (s, w, h)]) for (w, h) in _W(WIDTHS) for s in STATES]


def _skip(case, whs):
    """#42 - a case whose viewports all lie outside a push-time restriction measured nothing: a DECLARED skip, never a pass.
    Unrestricted it is never reached; if it were, it returns False and the caller's assertTrue fails - never silence."""
    if _ONLY is not None and not _W(whs):
        case.skipTest("#42 TV_LAW_WIDTHS=%s - this case is measured at %s only" % (LW.label(_ONLY), LW.label(sorted(set(whs)))))
    return False


def _need(case, whs):
    """#42 - the case measures at `whs`: go on, or skip as declared above"""
    case.assertTrue(_W(whs) or _skip(case, whs))


def _floor(full, whs):
    """#42 - a PRINT-THE-DENOMINATOR floor: the full run's own number; restricted, one per restricted column-layout
    viewport (900 wide and up) up to that number - never stricter than the full run's, so a restriction can only lose
    a red, never invent one (a lost red reads BLIND and refuses the push)"""
    if _ONLY is None:
        return full
    return min(full, len([x for x in _W(whs) if x[0] >= 900]))


class TheBuilderFitsAtEveryWidth(unittest.TestCase):

    def test_the_fixture_reached_the_builder_by_real_input(self):
        """PRINT THE DENOMINATOR: a builder that rendered nothing passes every check below."""
        r = _measure()
        self.assertTrue(r.get("opened"), "the Tools card did not open the builder")
        self.assertEqual([x for x in r["input"] if x], [], "a real press or drag did not land: %s" % r["input"])
        st = json.loads(r["store"] or "null")
        self.assertEqual(st, {"head": ["Crown of Ages", {"p2": 28}], "inv": [["Annihilus", 5, 2]]},
                         "the real-input flow did not leave Crown of Ages (roll 28) worn and Annihilus dragged to 6,3")
        # REG-1893 - a TV_LAW_WIDTHS restriction outside WIDTHS empties both loops below; the denominator case
        # then measured no width and passed. Same door as every sibling: go on, or a DECLARED skip.
        _need(self, WIDTHS)
        for label, m in _states():
            self.assertNotIn("err", m, "%s: %s" % (label, m.get("err")))
            self.assertGreaterEqual(m["nText"], 60, "%s: only %d text nodes measured" % (label, m["nText"]))
        for (w, h) in _W(WIDTHS):
            self.assertEqual((r["worn %dx%d" % (w, h)]["worn"], r["worn %dx%d" % (w, h)]["inv"]), (1, 1))
            self.assertGreater(r["picker %dx%d" % (w, h)]["opts"], 50, "%dx%d: the helm picker listed too little" % (w, h))
            self.assertGreaterEqual(r["edit %dx%d" % (w, h)]["rolls"], 4, "%dx%d: the Edit tab drew no roll boxes" % (w, h))
        self.assertEqual(r.get("errors"), [], "the page threw while the builder was open")

    def test_the_pickers_list_scrolls_to_its_last_row_under_a_real_wheel(self):
        r = _measure()
        bad = []
        _need(self, WHEEL_WIDTHS)
        for (w, h) in _W(WHEEL_WIDTHS):
            for slot in ("rarm", "feet"):
                x = r["wheel %s %dx%d" % (slot, w, h)]
                if "err" in x:
                    bad.append("%s %dx%d: %s" % (slot, w, h, x["err"]))
                    continue
                a = x["after"]
                if a["rows"] < 40:
                    bad.append("%s %dx%d: PRINT THE DENOMINATOR - only %d rows" % (slot, w, h, a["rows"]))
                if a["listH"] > h:
                    bad.append("%s %dx%d: the list is %dpx tall in a %dpx screen - unbounded, it cannot scroll" % (slot, w, h, a["listH"], h))
                if not a["lastSeen"]:
                    bad.append("%s %dx%d: after 40 wheel notches the last row (%s) is not on screen (scroll %s)"
                               % (slot, w, h, a["name"], a["scroll"]))
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_an_active_button_keeps_its_label_under_the_pointer(self):
        _need(self, (AT_2000,))
        hv = _measure()["hover"]
        bad = []
        for k in ("set", "quests", "filters", "class"):
            x = hv.get(k) or {}
            if "err" in x or not x:
                bad.append("%s: %s" % (k, x.get("err") if x else "not measured"))
            elif not x["hover"]:
                bad.append("%s: the pointer did not rest on it (%s) - UNKNOWN, not passing" % (k, x))
            elif x["color"] == x["bg"]:
                bad.append("%s %r: its text is %s on %s - the label disappears" % (k, x["text"], x["color"], x["bg"]))
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_no_word_or_control_is_cut_or_outside_its_panel(self):
        _need(self, WIDTHS)
        bad = []
        for label, m in _states():
            bad += ["%s %s" % (label, x) for x in m["cut"] + m["outside"]]
        self.assertEqual(bad, [], "text or a control in the builder is cut or spills out of its panel:\n  " + "\n  ".join(bad[:40]))

    def test_nothing_scrolls_sideways(self):
        _need(self, WIDTHS)
        bad = []
        for label, m in _states():
            if m["hscroll"][0] > m["hscroll"][1] + 1:
                bad.append("%s the window itself %d/%d" % (label, m["hscroll"][0], m["hscroll"][1]))
            bad += ["%s %s" % (label, x) for x in m["sideways"]]
        self.assertEqual(bad, [], "part of the builder scrolls sideways:\n  " + "\n  ".join(bad[:40]))

    def test_no_header_title_runs_under_its_control(self):
        _need(self, WIDTHS)
        bad = []
        for label, m in _states():
            bad += ["%s %s" % (label, x) for x in m["collide"]]
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_the_modal_is_on_screen_and_never_hides_the_slot_it_serves(self):
        _need(self, WIDTHS)
        bad, seen = [], 0
        for label, m in _states():
            if m["modal"] is None:
                continue
            if not m.get("modalInside"):
                bad.append("%s the modal leaves the viewport: %s" % (label, m["modal"]))
            if m["covered"] is not None:
                seen += 1
                if m["covered"]:
                    bad.append("%s the modal covers the glowing slot it serves" % label)
        self.assertGreaterEqual(seen, _floor(8, WIDTHS), "the slot-cover check ran in only %d column states" % seen)
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_stats_ends_inside_the_window_and_scrolls_its_own_rows(self):
        """#174 R2 — the Grok seat on R1: "the stats column is cut off at the bottom edge ... rows from Energy down are
        sliced". In columns STATS ends inside the window and its row list scrolls inside it; every row is reachable
        without scrolling the whole builder."""
        _need(self, WIDTHS)
        bad, seen = [], 0
        for w, h in _W(WIDTHS):
            m = _measure()["plain %dx%d" % (w, h)]
            if m.get("stack"):
                continue
            seen += 1
            if m.get("statsBottom") is None or m["statsBottom"] > m["vh"] + 0.5:
                bad.append("%dx%d: STATS ends %s px past the window's bottom (%s)" % (w, h, None if m.get("statsBottom") is None else round(m["statsBottom"] - m["vh"], 1), m.get("statsBottom")))
            sl = m.get("statsList")
            if not sl or sl[2] not in ("auto", "scroll"):
                bad.append("%dx%d: the stats list does not scroll inside its panel: %s" % (w, h, sl))
        self.assertGreaterEqual(seen, _floor(4, WIDTHS), "PRINT THE DENOMINATOR: only %d column layouts measured" % seen)
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_at_2000_the_columns_are_their_literal_322_716_300(self):
        _need(self, (AT_2000,))
        bad = []
        for state in ("plain", "worn"):
            m = _measure()["%s 2000x1300" % state]
            self.assertFalse(m["stack"])
            for c, (x, wd) in THEIR_COLS.items():
                got = m["cols"][c]
                if not got or abs(got[0] - x) > TOL or abs(got[2] - wd) > TOL:
                    bad.append("%s %s: theirs x=%d w=%d, measured %s" % (state, c, x, wd, [round(v, 1) for v in got] if got else None))
            # #174 R1 — his order: "both inventory and character together because the charms are related". The doll
            # and its 10x4 inventory SHARE the 716 centre: the doll is still big (their 292 wide x >= 1.35) and the
            # inventory sits directly under it, as wide as the doll, inside the EQUIPMENT view
            dl, iv = m["doll"], m.get("invRect")
            if not dl or dl[2] < 292 * 1.35:
                bad.append("%s the doll is not big in the centre: %s" % (state, dl))
            if not m.get("invInMain") or not iv:
                bad.append("%s the inventory is not in the EQUIPMENT view with the doll: %s" % (state, iv))
            elif not (iv[1] >= dl[1] + dl[3] and abs((iv[0] + iv[2] / 2) - (dl[0] + dl[2] / 2)) <= 2
                      and abs(iv[2] - dl[2]) <= 0.08 * dl[2]):
                bad.append("%s the inventory %s is not under the doll %s at its width" % (state, iv, dl))
            if m["fsTitle"] is None or abs(m["fsTitle"] - m["tokTitle"]) > 0.05:
                bad.append("%s the header type %s is not the --fs-title token %s at k=1" % (state, m["fsTitle"], m["tokTitle"]))
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_the_edit_tab_with_picked_mods_and_add_mod_open_fits(self):
        """#174 v-B3 - a rare Diadem with four picked mods (shut, and with ADD MOD open) and a magic Grand Charm with two
        (and with its prefix alone and ADD MOD open, its suffixes listed): nothing cut, nothing outside its panel,
        nothing sideways, the modal on screen and off the glowing slot"""
        _need(self, MOD_WIDTHS)
        r, bad = _measure(), []
        for (w, h) in _W(MOD_WIDTHS):
            for state in MOD_STATES:
                label = "%s %dx%d" % (state, w, h)
                m = r[label]
                if "err" in m:
                    bad.append("%s: %s" % (label, m["err"]))
                    continue
                want = MOD_ROWS[state]
                if m["mods"] != want:
                    bad.append("%s: PRINT THE DENOMINATOR - %d picked-mod rows drawn, %d picked" % (label, m["mods"], want))
                if state.endswith("addmod") and m["addOpts"] < 20:
                    bad.append("%s: the open ADD MOD list drew only %d options" % (label, m["addOpts"]))
                if m["nText"] < 40:
                    bad.append("%s: only %d text nodes measured" % (label, m["nText"]))
                bad += ["%s %s" % (label, x) for x in m["cut"] + m["outside"] + m["sideways"] + m["collide"]]
                if m["hscroll"][0] > m["hscroll"][1] + 1:
                    bad.append("%s the window itself scrolls sideways %d/%d" % (label, m["hscroll"][0], m["hscroll"][1]))
                if m["modal"] is None or not m.get("modalInside"):
                    bad.append("%s the modal is not on screen: %s" % (label, m["modal"]))
                if m["covered"]:
                    bad.append("%s the modal covers the glowing slot it serves" % label)
            dm = r["mods %dx%d" % (w, h)]
            if "err" not in dm and dm["rolls"] < 2:
                bad.append("mods %dx%d: Ruby 31-40 and of the Tiger 21-30 drew %d roll boxes" % (w, h, dm["rolls"]))
        self.assertEqual(bad, [], "\n  ".join(bad[:40]))

    def test_the_open_add_mod_list_takes_the_room_of_its_tab(self):
        """#174 v-B3 fix round - the open list lies wholly inside the Edit tab's visible box, and where it has more options
        than fit it runs to that box's bottom: a fixed calc(330 x u) ran ~137px below the modal at 1280x800 (5 of 218
        options in view) and stopped at 158px on a phone with ~220px empty under it"""
        _need(self, MOD_WIDTHS)
        r, bad = _measure(), []
        for (w, h) in _W(MOD_WIDTHS):
            for state in ("addmod", "gcaddmod"):
                label = "fit %s %dx%d" % (state, w, h)
                f = r.get(label)
                if not f:
                    bad.append("%s: no ADD MOD list was measured" % label)
                    continue
                if f["top"] < f["edTop"] - 0.5 or f["bottom"] > f["edBottom"] + 0.5:
                    bad.append("%s: the list (%.0f..%.0f) runs outside the tab's visible box (%.0f..%.0f)" % (label, f["top"], f["bottom"], f["edTop"], f["edBottom"]))
                if f["sh"] > f["ch"] + 1 and f["edBottom"] - f["bottom"] > 40:
                    bad.append("%s: the list stops at %dpx with %.0fpx of the tab empty under it (%d options)" % (label, f["ch"], f["edBottom"] - f["bottom"], f["opts"]))
                if f["seen"] < min(8, f["opts"]):
                    bad.append("%s: PRINT THE DENOMINATOR - %d of %d options in view" % (label, f["seen"], f["opts"]))
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_add_mod_is_a_combobox_by_real_keys(self):
        """#174 v-B3 fix round - their ADD MOD paints the active option, so Enter's pick is seen: by REAL key input, the
        search box keeps focus through ArrowDown, names the active option (aria-activedescendant), which is the one
        painted, the second after one ArrowDown; Enter adds exactly that option"""
        _need(self, (AT_2000,))
        r = _measure()
        self.assertEqual([x for x in r["input"] if x], [], "a real press missed")
        c = r["combo"]
        self.assertEqual((c["typed"]["focus"], c["typed"]["role"]), ("cb-add-q", "combobox"))
        self.assertEqual(c["typed"]["acts"], 1, "after typing, not exactly one option is active: %s" % c["typed"])
        self.assertEqual(c["down"]["focus"], "cb-add-q", "ArrowDown took the focus out of the search box")
        self.assertEqual(c["down"]["active"], c["down"]["second"], "ArrowDown did not make the second option active: %s" % c["down"])
        self.assertNotIn(c["down"]["painted"], (None, "rgba(0, 0, 0, 0)", "transparent"), "the active option is not painted: %s" % c["down"])
        self.assertEqual(c["down"]["acts"], 1)
        self.assertEqual(c["enter"]["stored"], ["p712", "s175", c["down"]["activeId"]],
                         "Enter did not add the painted option %s: %s" % (c["down"]["activeId"], c["enter"]))

    def test_round2_the_pointer_and_the_keys_light_one_row(self):
        """#174 round 2 (the Grok seat on v3509, img3): the keyboard's active option and the row under the pointer were
        painted in one gold, so two rows lit and nothing said which one Enter adds. By REAL input: the pointer at rest on
        the 4th option makes it the one active and the ONLY one painted; a real ArrowDown with the pointer still there
        moves the active option on, and still exactly one row is painted"""
        _need(self, (AT_2000,))
        r = _measure()
        self.assertEqual([x for x in r["input"] if x], [], "a real press or pointer move missed")
        p, d = r["lit"]["pointer"], r["lit"]["down"]
        self.assertGreater(p["n"], 4, "PREMISE: the open list has too few options to point at the 4th: %s" % p)
        self.assertEqual(p["under"], 3, "PREMISE: the pointer is not on the 4th option: %s" % p)
        self.assertEqual((p["active"], p["lit"]), (3, [3]), "the row under the pointer is not the one active and the only one lit: %s" % p)
        self.assertEqual((d["active"], d["lit"]), (4, [4]), "after ArrowDown under a still pointer, not exactly the new active row is lit: %s" % d)

    def test_round2_a_wrapped_stat_label_sets_its_second_line_in(self):
        """#174 round 2 (the Grok seat on v3509, img2 AND img3): "Fire" / "Resistance" with the value on the first line
        read as a row "Resistance" with no value. Every label that wraps sets its continuation line in (a hanging indent),
        so the second line reads as the rest of the label - v-B2's rule (the value keeps the first line) stands"""
        _need(self, (AT_INDENT,))
        rows = _measure()["indent"]
        self.assertGreater(len(rows), 0, "PREMISE: no stat label wraps at 1280, so this measured nothing")
        flat = ["%s (first %.1f, next %.1f)" % (x["text"], x["first"], x["next"]) for x in rows if x["next"] - x["first"] < 2]
        self.assertEqual(flat, [], "these labels wrap flush, so their second line reads as a row of its own: %s" % flat)

    def test_round3_the_indent_costs_no_row_its_first_line_at_any_width(self):
        """#174 round 3 (the Grok seat on v3510, measured): round 2's hanging indent padded the label, the padding counted
        toward its min-content, and at 6 of 56 widths a value dropped under its label - v-B2's rule undone by the fix
        for the next complaint. Swept every 20px of the tight band (900-1400) against the same page with the indent
        taken away: the indent makes NO extra value drop, and no label text runs under its value"""
        _need(self, SWEEP_AT)
        sw = _measure()["sweep"]
        self.assertEqual(len(sw), len(_W(SWEEP_AT)), "PREMISE: the band was not swept end to end: %d of %d widths" % (len(sw), len(_W(SWEEP_AT))))
        extra = [(x["w"], x["extra"]) for x in sw if x["extra"]]
        over = [(x["w"], x["over"]) for x in sw if x["over"]]
        self.assertEqual(extra, [], "the indent pushed these values under their labels (v-B2's rule): %s" % extra)
        self.assertEqual(over, [], "label text runs under its value at these widths: %s" % over)

    def test_round8_a_number_never_leaves_its_labels_first_line(self):
        """#29(a) 2026-09-28, measured on v3521: round 3 held only that the INDENT adds no drop - a value could still drop
        for its own width. One resistance carrying a rolled range ("-50 to -40% RANGE <=75%") put its value on a line of
        its own ALONE at 960-1180 while the three beside it kept theirs, and at 900-940 all four dropped. Every 20px of
        900-1400, as the build stands AND with Fire alone widened: no value's number sits below its label's first line,
        no part of a value (number, chip, cap) lies outside its row or past STATS' edge, no label text runs under a value.
        This holds round 3's rule at every width, so round 3's own sabotage (the indent's margin) is retired with it"""
        _need(self, SWEEP_AT)
        sw = _measure()["sweep"]
        self.assertEqual(len(sw), len(_W(SWEEP_AT)), "PREMISE: the band was not swept end to end: %d of %d widths" % (len(sw), len(_W(SWEEP_AT))))
        unwidened = [x["w"] for x in sw if not (x.get("widened") or "").startswith("\u221250 to \u221240%")]
        self.assertEqual(unwidened, [], "PREMISE: the Fire row was not widened at these widths, so the one-wide-row case measured nothing")
        for key, what in (("real", "as the build stands"), ("wide", "with Fire alone widened")):
            drop = [(x["w"], x[key]) for x in sw if x[key]]
            self.assertEqual(drop, [], "a value left its label's first line %s: %s" % (what, drop))
        for key, what in (("spill", "as the build stands"), ("wspill", "with Fire alone widened")):
            out = [(x["w"], x[key]) for x in sw if x[key]]
            self.assertEqual(out, [], "a part of a value lies outside its row %s: %s" % (what, out))
        over = [(x["w"], x["wover"]) for x in sw if x["wover"]]
        self.assertEqual(over, [], "label text runs under a widened value: %s" % over)

    def test_round7_a_pick_never_covers_stats_and_a_charm_shows_its_art(self):
        """#174 round 7 (2026-09-26, measured): their STATS update while you pick and edit, so they stay in view - an
        inventory cell's picker fell back to the PAGE centre at 1120-1280 and covered STATS' left edge by 25-28px (a
        slot's never did). Every pick measured here (a slot's Select / Edit / mods / ADD MOD, a charm's mods / ADD MOD),
        side-by-side layout: the modal ends left of STATS. #174 v-B4: the grid sits in the template panel now, so an
        inventory cell's picker takes the side away from the GRID; its page-centre fallback is still reached at 1024x768
        and 901x900, so an inventory cell's Select is measured at every width. And a Grand Charm's Edit tile draws its in-game sprite - it
        printed "Grand Charm" in a box because only Small Charm was ever registered by its base name"""
        _need(self, WIDTHS + MOD_WIDTHS)
        r, bad, seen = _measure(), [], 0
        for key, m in r.items():
            if not isinstance(m, dict) or not m.get("modal") or not m.get("cols") or m.get("stack"):
                continue
            if not key.split(" ")[0] in ("picker", "edit", "mods", "addmod", "gcmods", "gcaddmod", "invpick"):
                continue
            seen += 1
            # the modal rect is in the VIEWPORT frame; cols.* are relative to the builder box - compare like with like
            ml, mw, sl = m["modal"][0], m["modal"][2], m.get("statsLeftAbs")
            if sl is None:
                bad.append("%s: STATS' left edge was not measured" % key)
                continue
            if ml + mw > sl + 0.5:
                bad.append("%s: the modal ends at %.0f, STATS starts at %.0f (%.0fpx covered)" % (key, ml + mw, sl, ml + mw - sl))
        self.assertGreaterEqual(seen, _floor(11, WIDTHS + MOD_WIDTHS), "PREMISE: only %d pick states with a modal were measured" % seen)
        self.assertEqual(bad, [], "a pick covers STATS, which their Edit keeps in view: %s" % bad)
        arts = dict((k, v) for k, v in r.items() if k.startswith("gcart "))
        self.assertEqual(len(arts), len(_W(MOD_WIDTHS)) * 2, "PREMISE: the charm's art was not probed at every width: %s" % sorted(arts))
        noart = [k for k, v in arts.items() if not v["img"] or v["failed"]]
        self.assertEqual(noart, [], "a Grand Charm's Edit tile has no art (its name in a box): %s" % noart)

    def test_under_900_the_character_comes_first(self):
        _need(self, WIDTHS)
        for (w, h) in _W(WIDTHS):
            m = _measure()["worn %dx%d" % (w, h)]
            if w >= 900:
                self.assertFalse(m["stack"], "%dx%d stacked" % (w, h))
                continue
            self.assertTrue(m["stack"], "%dx%d did not stack" % (w, h))
            self.assertLess(m["cols"]["main"][1], m["cols"]["stats"][1], "%dx%d: the doll is not above the stats" % (w, h))
            self.assertLess(m["cols"]["main"][1], m["cols"]["left"][1], "%dx%d: the doll is not above the inventory" % (w, h))

    def test_v_b4_the_character_and_its_inventory_are_one_panel_the_games_grid_flush_under_the_doll(self):
        """#174 v-B4 - his words: "the character template is actually an inventory/character template they always open and
        are seen as a set together" and "the INVENTORY under the equipment need to be structured like this JUST LIKE IT IS
        IN GAME one to one". Theirs (planner 60/61, 15_crop): ONE carved-stone panel, the doll and flush under it the 10x4
        grid - black cells, thin lines, no gaps, no rounded corners. v3514's was a framed doll, a caption, then a separate
        grid with 2px gaps and rounded cells. In every plain / worn state at the 7 widths and with three charms at the
        builder's 5 sizes: the grid and the doll lie inside the one panel, flush (<= 12px, no word between), the caption
        and the status line under it, 10 x 4 equal square cells edge to edge, radius 0, the grid never wider than the
        doll's inner width, cells >= 26px from 1280 up, every item inside its cells"""
        _need(self, WIDTHS + TPL_WIDTHS)
        r, bad = _measure(), []
        tpl = sorted(k for k in r if k.startswith("tpl ") and isinstance(r[k], dict) and k != "tpl before")
        want = ["tpl %s %dx%d" % (s, w, h) for s in ("plain", "worn") for (w, h) in _W(WIDTHS)] + \
               ["tpl charms %dx%d" % (w, h) for (w, h) in _W(TPL_WIDTHS)]
        self.assertEqual(sorted(want), tpl, "PRINT THE DENOMINATOR: the template was not measured in every state")
        for k in want:
            m = r[k]
            if "err" in m:
                bad.append("%s: %s" % (k, m["err"]))
                continue
            w = int(k.rsplit(" ", 1)[1].split("x")[0])
            p, dl, g = m["panel"], m["doll"], m["grid"]
            inside = lambda a: a[0] >= p[0] - 0.5 and a[1] >= p[1] - 0.5 and a[2] <= p[2] + 0.5 and a[3] <= p[3] + 0.5
            if not (m["gridInDom"] and inside(g)):
                bad.append("%s: the inventory %s is not inside the template panel %s (in its markup: %s)"
                           % (k, [round(v) for v in g], [round(v) for v in p], m["gridInDom"]))
            if not (m["dollInDom"] and inside(dl)):
                bad.append("%s: the doll %s is not inside the template panel %s" % (k, [round(v) for v in dl], [round(v) for v in p]))
            gap = g[1] - dl[3]
            if gap < -0.5 or gap > TPL_FLUSH:
                bad.append("%s: the grid's top is %.1fpx from the doll's bottom - not flush (theirs ~9, at most %d)" % (k, gap, TPL_FLUSH))
            if m["between"]:
                bad.append("%s: words between the doll and its inventory: %s" % (k, m["between"]))
            b = m["below"]
            for nm in ("caption", "status"):
                if b[nm] is None or b[nm + "InPanel"] or b[nm][1] < p[3] - 0.5:
                    bad.append("%s: the %s line is not under the template panel (%s, panel ends at %.0f)" % (k, nm, b[nm], p[3]))
            if m["nCells"] != 40 or len(m["cols"]) != 10 or len(m["rows"]) != 4:
                bad.append("%s: PRINT THE DENOMINATOR - %d cells, %d columns, %d rows (10 x 4)" % (k, m["nCells"], len(m["cols"]), len(m["rows"])))
                continue
            cw, ch = m["cellW"], m["cellH"]
            if max(cw) - min(cw) > 0.05 or max(ch) - min(ch) > 0.05 or abs(cw[0] - ch[0]) > 0.05:
                bad.append("%s: the cells are not equal squares (widths %.2f-%.2f, heights %.2f-%.2f)" % (k, min(cw), max(cw), min(ch), max(ch)))
            seams = [round(m["cols"][i + 1][0] - m["cols"][i][1], 2) for i in range(9)] + \
                    [round(m["rows"][i + 1][0] - m["rows"][i][1], 2) for i in range(3)]
            if any(abs(s) > 0.05 for s in seams) or any(x not in ("0px", "normal") for x in m["gap"]):
                bad.append("%s: the cells are not edge to edge - gap %s, seams %s" % (k, m["gap"], seams))
            if m["radius"] != ["0px"] * 4 or m["cellRadius"] != ["0px 0px 0px 0px"]:
                bad.append("%s: rounded corners - grid %s, cells %s" % (k, m["radius"], m["cellRadius"]))
            cbx = m["cellsBox"]
            if not (cbx[0] >= g[0] - 0.5 and cbx[1] >= g[1] - 0.5 and cbx[2] <= g[2] + 0.5 and cbx[3] <= g[3] + 0.5) or not inside(cbx):
                bad.append("%s: the cells %s spill out of their grid %s / the panel %s"
                           % (k, [round(v) for v in cbx], [round(v) for v in g], [round(v) for v in p]))
            span = max(g[2], cbx[2]) - min(g[0], cbx[0])
            if span > m["dollInner"] + 0.5:
                bad.append("%s: the grid and its cells (%.1fpx) are wider than the doll's inner width (%dpx)" % (k, span, m["dollInner"]))
            if w >= 1280 and cw[0] < TPL_MIN_CELL:
                bad.append("%s: a cell is %.1fpx - under %dpx from 1280 up" % (k, cw[0], TPL_MIN_CELL))
            for it in m["items"]:
                c, rc = it["cells"], it["rect"]
                if not c or rc[0] < c[0] - 0.5 or rc[1] < c[1] - 0.5 or rc[2] > c[2] + 0.5 or rc[3] > c[3] + 0.5:
                    bad.append("%s: %s at %s is drawn at %s, outside its cells %s" % (k, it["name"], it["at"], [round(v, 1) for v in rc], c and [round(v, 1) for v in c]))
            if k.startswith("tpl worn") and len(m["items"]) != 1:
                bad.append("%s: PRINT THE DENOMINATOR - %d items drawn, Annihilus alone was placed" % (k, len(m["items"])))
        # the three charms: placed through the cell's own picker, each drawn with its art in its cells, and they MOVE the stats
        placed = r.get("tpl placed") or []
        self.assertEqual(r.get("tpl new"), "ok", "the builder's + New build did not make a fresh build: %s" % r.get("tpl new"))
        self.assertEqual([(x.get("n"), x.get("ok")) for x in placed], [(n, True) for (n, _, _, _) in TPL_CHARMS],
                         "a charm was not placed through the inventory's picker: %s" % placed)
        before = r["tpl before"]
        self.assertNotIn("err", before, before.get("err"))
        self.assertEqual(before["items"], [], "PREMISE: the fresh build's inventory is not empty")
        for (w, h) in _W(TPL_WIDTHS):
            m = r["tpl charms %dx%d" % (w, h)]
            if "err" in m:
                continue
            got = sorted((it["name"], tuple(it["at"][:2]), it["art"]) for it in m["items"])
            exp = sorted((n, (x, y), True) for (n, x, y, _) in TPL_CHARMS)
            if got != exp:
                bad.append("charms %dx%d: drawn %s, placed %s (name, cell, art)" % (w, h, got, exp))
            for key in ("allSkills", "strength"):
                if m["stats"][key] is None or before["stats"][key] is None or m["stats"][key] == before["stats"][key]:
                    bad.append("charms %dx%d: the charms did not move STATS' %s (%s before, %s with them)"
                               % (w, h, key, before["stats"][key], m["stats"][key]))
        self.assertEqual(bad, [], "the character/inventory template is not one panel with the game's grid:\n  " + "\n  ".join(bad[:40]))

    def test_v_b4_fix_every_tile_is_one_indigo_whatever_its_quality_and_green_while_edited(self):
        """#174 v-B4 fix round - theirs and the game draw every item in the grid on ONE indigo whatever its quality (a
        unique Annihilus and Hellfire Torch and a magic charm alike, (8,2,28) over the black cell, no frame, no halo); the
        one being edited is green. Ours filled a unique gold with a gold border and a gold bloom, a magic one blue."""
        _need(self, (AT_2000,))
        lv = _measure().get("tiles") or {}
        m = lv.get("max") or {}
        self.assertNotIn("err", m, m.get("err"))
        tiles, bad = m.get("tiles") or [], []
        self.assertEqual(sorted(x["name"] for x in tiles), sorted(n for (n, _, _, _) in TPL_CHARMS),
                         "PRINT THE DENOMINATOR: the tiles drawn are not the three charms placed")
        quals = sorted(set(x["q"] for x in tiles))
        self.assertGreaterEqual(len(quals), 2, "PREMISE: the placed charms carry one quality only (%s), so a fill by quality "
                                               "could not show" % quals)
        self.assertEqual([x["name"] for x in tiles if x["red"] or x["sel"]], [],
                         "PREMISE: at the build's own level %s no tile may be red or in Edit" % m.get("level"))
        cell = _rgba(m.get("cellBg"))
        fills = sorted(set(x["bg"] for x in tiles))
        if len(fills) != 1:
            bad.append("the tiles' fill follows the quality: %s" % [(x["name"], x["q"], x["bg"]) for x in tiles])
        for x in tiles:
            seen = _over(_rgba(x["bg"]), cell)
            if cell is None or seen is None or max(abs(a - b) for a, b in zip(seen, THEIR_TILE)) > TILE_TOL:
                bad.append("%s (%s): its tile reads %s over the cell %s - theirs %s" % (x["name"], x["q"], seen, cell, THEIR_TILE))
            bw, bc = x["border"]
            if bw not in ("0px",) and (_rgba(bc) or (0, 0, 0, 1))[3] > 0.01:
                bad.append("%s (%s): its tile has a visible frame %s %s - theirs has none" % (x["name"], x["q"], bw, bc))
            if x["filter"] != "none":
                bad.append("%s (%s): its art carries a bloom %r - theirs is the bare art" % (x["name"], x["q"], x["filter"]))
        s = lv.get("sel") or {}
        self.assertIsNone(lv.get("press"), "the Grand Charm's tile could not be pressed by real input: %s" % lv.get("press"))
        on = [x for x in s.get("tiles") or [] if x["sel"]]
        self.assertEqual([x["name"] for x in on], ["Grand Charm"], "pressing the Grand Charm's tile did not mark it edited")
        seen = _over(_rgba(on[0]["bg"]), cell)
        if seen is None or max(abs(a - b) for a, b in zip(seen, THEIR_EDITED)) > TILE_TOL:
            bad.append("the edited tile reads %s over the cell - theirs %s" % (seen, THEIR_EDITED))
        rest = sorted(set(x["bg"] for x in s.get("tiles") or [] if not x["sel"]))
        if rest != fills:
            bad.append("with one tile edited the others read %s, not the indigo %s" % (rest, fills))
        self.assertEqual(bad, [], "an inventory tile is coloured by its quality, not its state:\n  " + "\n  ".join(bad))

    def test_v_b4_fix_a_charm_its_level_cannot_use_is_red_and_counts_for_nothing(self):
        """#174 v-B4 fix round - in the game a charm below its level requirement gives no bonus and its background turns
        red. Ours kept the tile gold and STATS summed it: Annihilus (Required Level 70) at level 50 read All Skills 1
        EXACT. Every tile red exactly when its own tooltip's Required Level is above the build's level, at three levels;
        STATS leaves the red ones out and names them; Calculations lists them among the failed requirements."""
        _need(self, (AT_2000,))
        r = _measure()
        lv = r.get("tiles") or {}
        mx = lv.get("max") or {}
        need = dict((x["name"], x["need"]) for x in mx.get("tiles") or [])
        anni, gheed = need.get("Annihilus") or 0, need.get("Gheed's Fortune") or 0
        self.assertTrue(anni > gheed > 1, "PREMISE: the tooltips' Required Levels do not separate the two uniques "
                                          "(Annihilus %s, Gheed's Fortune %s)" % (anni, gheed))
        mid, low = lv.get("mid") or {}, lv.get("low") or {}
        for nm, m in (("mid", mid), ("low", low)):
            self.assertNotIn("err", m, "%s: %s" % (nm, m.get("err")))
        self.assertEqual(mid.get("level"), gheed, "the build is not at Gheed's Fortune's Required Level")
        self.assertIsNone(lv.get("down"), "the level's down arrow could not be pressed by real input: %s" % lv.get("down"))
        self.assertEqual(low.get("level"), gheed - 1, "the down arrow did not lower the level by one")
        self.assertEqual(lv.get("helm"), "ok", "Crown of Ages was not equipped on the fresh build: %s" % lv.get("helm"))
        crown = dict((x["name"], x["need"]) for x in mx.get("worn") or []).get("Crown of Ages") or 0
        self.assertTrue(crown > gheed, "PREMISE: Crown of Ages' Required Level (%s) is not above Gheed's Fortune's (%s), so the "
                                       "worn half is never tested" % (crown, gheed))
        bad = []
        for nm, m in (("max", mx), ("mid", mid), ("low", low)):
            if len(m.get("tiles") or []) != len(TPL_CHARMS) or len(m.get("worn") or []) != 1:
                bad.append("%s: PRINT THE DENOMINATOR - %d tiles, %d worn" % (nm, len(m.get("tiles") or []), len(m.get("worn") or [])))
            for x in m.get("tiles") or []:
                want = x["need"] > m["level"]
                if x["red"] != want:
                    bad.append("level %d: %s (Required Level %d) is %s" % (m["level"], x["name"], x["need"], "red" if x["red"] else "not red"))
                if want and ("needs level %d" % x["need"]) not in x["label"]:
                    bad.append("level %d: %s's tile does not SAY it needs level %d: %r" % (m["level"], x["name"], x["need"], x["label"]))
            # the WORN half of the same rule: the doll's red slot is left out of STATS too, and named
            for x in m.get("worn") or []:
                want = x["need"] > m["level"]
                if x["red"] != want:
                    bad.append("level %d: the doll's %s (%s, Required Level %d) is %s" % (m["level"], x["slot"], x["name"], x["need"], "red" if x["red"] else "not red"))
                named = any(x["name"] in t and ("needs level %d" % x["need"]) in t for t in m.get("notes") or [])
                if named != want:
                    bad.append("level %d: STATS %s %s (Required Level %d) as left out: %s" % (m["level"], "does not name" if want else "names", x["name"], x["need"], m.get("notes")))
        before = (r.get("tpl before") or {}).get("stats") or {}
        a0, am, ax = before.get("allSkills"), mid["stats"].get("All Skills"), mx["stats"].get("All Skills")
        if am != a0 or ax == a0:
            bad.append("All Skills: %r with no charms, %r at the max level, %r at level %d where Annihilus (level %d) cannot be "
                       "used - it must read as with no charms" % (a0, ax, am, gheed, anni))
        gm, gl, gx = mid["stats"].get("Gold Find"), low["stats"].get("Gold Find"), mx["stats"].get("Gold Find")
        if gm != gx or gl == gx:
            bad.append("Gold Find: %r at the max level, %r at level %d (Gheed's Fortune counts), %r at level %d (it cannot)"
                       % (gx, gm, gheed, gl, gheed - 1))
        said = lambda m, n, lvl: any(n in t and ("needs level %d" % lvl) in t for t in m.get("notes") or [])
        if not said(mid, "Annihilus", anni) or said(mid, "Gheed's Fortune", gheed):
            bad.append("level %d: STATS' notes do not name exactly Annihilus as left out: %s" % (gheed, mid.get("notes")))
        if not (said(low, "Annihilus", anni) and said(low, "Gheed's Fortune", gheed)):
            bad.append("level %d: STATS' notes do not name both uniques as left out: %s" % (gheed - 1, low.get("notes")))
        mc, lc = lv.get("midCalc") or "", lv.get("lowCalc") or ""
        if "Annihilus" not in mc or "Gheed's Fortune" in mc or "Gheed's Fortune" not in lc:
            bad.append("Calculations' failed requirements: %r at level %d, %r at level %d" % (mc, gheed, lc, gheed - 1))
        self.assertEqual(bad, [], "a charm the level cannot use is not red, or still feeds STATS:\n  " + "\n  ".join(bad))

    def test_round9_an_edit_window_is_as_tall_as_what_it_holds(self):
        """#29(d) his answer 2026-09-28 ("TIGHTEN"): the Edit window is sized to its content - no empty lower third. In every
        Edit state measured: at most EMPTY_MAX px of its body lies empty under its last line, and when its body scrolls, at
        most EMPTY_MAX px of the glass is free under the window (it took the room before it scrolled)"""
        _need(self, WIDTHS)
        r, bad, seen = _measure(), [], 0
        for key, f in sorted(r.items()):
            if not key.startswith("edfit "):
                continue
            seen += 1
            if "err" in f:
                bad.append("%s: %s" % (key, f["err"]))
                continue
            if f["n"] < 2:
                bad.append("%s: PRINT THE DENOMINATOR - the Edit body drew %d block(s)" % (key, f["n"]))
            if f["empty"] > EMPTY_MAX:
                bad.append("%s: %.0fpx of the Edit window lies empty under its last line (window %s)" % (key, f["empty"], [round(v) for v in f["modal"]]))
            if f["sh"] > f["ch"] + 1 and f["free"] > EMPTY_MAX:
                bad.append("%s: it scrolls %dpx inside itself with %.0fpx of the glass free under it" % (key, f["sh"] - f["ch"], f["free"]))
        # #42 - one helm Edit per width and two mod Edits per mod width, counted over the widths this run measures
        self.assertGreaterEqual(seen, len(_W(WIDTHS)) + 2 * len(_W(MOD_WIDTHS)), "PREMISE: only %d Edit states were measured" % seen)
        self.assertEqual(bad, [], "an Edit window is not sized to what it holds:\n  " + "\n  ".join(bad))

    def test_round9_a_range_hint_in_a_number_box_is_shown_whole(self):
        """#29(d) (the Grok CLI's cold look at v3522): the helm's Sockets box read "1-" - Chrome sizes an input[type=number] by
        its max's digits, so a box whose max is 2 is one digit wide and its range hint "1-2" was cut under the spin arrows.
        In every Edit state: every number box with a range hint gives it its text width plus the arrows (14px). Its first
        run found a second one: the rare Diadem's Defense box (a base's Edit row) read "50-6" at 375"""
        _need(self, WIDTHS)
        r, bad, seen = _measure(), [], 0
        for key, f in sorted(r.items()):
            if not key.startswith("edfit ") or "err" in f:
                continue
            for p in f.get("ph") or []:
                seen += 1
                if p["room"] < p["text"] + 14:
                    bad.append("%s #%s: the hint %r needs %.0fpx and its box gives %.0fpx" % (key, p["id"], p["ph"], p["text"] + 14, p["room"]))
        self.assertGreaterEqual(seen, len(_W(WIDTHS)), "PREMISE: only %d range hints were measured (the helm's Sockets at every width)" % seen)
        self.assertEqual(bad, [], "a range hint is cut in its box:\n  " + "\n  ".join(bad))

    def test_round9_the_builders_tabs_stay_in_view_while_a_modal_is_open(self):
        """#29(d) his answer 2026-09-28: the builder's tabs stay visible while the Edit window is open - at 1280x800 it was
        pulled up over EQUIPMENT, the tab it was editing for, and on a phone the sheet covered the whole glass. In every state
        with a modal, where the tab row is on the glass with room under it: the modal does not overlap the row, and each
        tab's centre hit-tests to that tab"""
        _need(self, WIDTHS)
        r, bad, seen = _measure(), [], 0
        for key, tb in sorted(r.items()):
            if not key.startswith("tabs "):
                continue
            if not tb.get("modal"):
                bad.append("%s: PREMISE - no modal was open in a modal state" % key)
                continue
            if "err" in tb:
                bad.append("%s: %s" % (key, tb["err"]))
                continue
            if not tb["onScreen"] or tb["room"] < 280:
                continue          # the row is off the glass (or has no room under it): nothing to keep in view here
            seen += 1
            if tb["over"]:
                bad.append("%s: the modal %s lies over the tab row %s" % (key, [round(v) for v in tb["at"]], [round(v) for v in tb["tabs"]]))
            hidden = [x["tab"] for x in tb["hit"] if not x["seen"]]
            if hidden or len(tb["hit"]) != 3:
                bad.append("%s: tabs not in view: %s (of %d)" % (key, hidden, len(tb["hit"])))
        self.assertGreaterEqual(seen, 3 * len(_W(WIDTHS)), "PREMISE: the tab row was checked in only %d modal states" % seen)
        self.assertEqual(bad, [], "a modal hides the builder's tabs:\n  " + "\n  ".join(bad))

    def test_r2_his_cap_words_cost_no_label_a_line(self):
        """REG-1376 (round 2, reproduced on fe817ab7): his ruling is the words "cap 75%" (kept), and on the number's line they
        widened the value so its label wrapped once more - Physical Damage Reduction 2 -> 3 lines at 1280x800, Lightning
        Resistance 1 -> 2 at 1280 and 2000. At every width, plain and with the helm worn: every capped row's label has the
        lines it has with the chip taken away; the chip is one line and lies inside its row. PREMISE: the eight capped rows
        (four resistances, three absorbs, damage reduction) at 1280x800 and 901x900 in both states"""
        _need(self, WIDTHS)
        r, bad, seen = _measure(), [], {}
        for key, rows in sorted(r.items()):
            if not key.startswith("caps "):
                continue
            seen[key] = len(rows)
            for x in rows:
                if x["n"] != x["bare"]:
                    bad.append("%s: %s is %d line(s) beside %r and %d without it" % (key, x["k"], x["n"], x["cap"], x["bare"]))
                if x["capLines"] != 1:
                    bad.append("%s: %s's chip %r wraps onto %d lines" % (key, x["k"], x["cap"], x["capLines"]))
                if not x["capIn"]:
                    bad.append("%s: %s's chip %r lies outside its row" % (key, x["k"], x["cap"]))
                if not x["cap"].startswith("cap "):
                    bad.append("%s: %s's chip reads %r, not his words 'cap N%%'" % (key, x["k"], x["cap"]))
        for size in [LW.label([x]) for x in _W(((1280, 800), (901, 900)))]:       # #42 - the two it names, where measured
            for state in ("plain", "worn"):
                self.assertGreaterEqual(seen.get("caps %s %s" % (state, size), 0), 8,
                                        "PREMISE: %s %s measured %s capped rows, not the eight" % (state, size, seen.get("caps %s %s" % (state, size))))
        self.assertEqual(bad, [], "the cap chip costs a STATS label a line:\n  " + "\n  ".join(bad))

    def test_r2_the_builder_is_as_tall_as_what_it_holds(self):
        """REG-1379 his "Tighten both" (round 2): at every width, plain and worn - where the window does not scroll it ends
        under its content by its own bottom padding (no band) and STATS ends with the columns beside it (it was the glass's
        height whatever stood there, ~270px past them at 2000x1300); where it scrolls it is the glass's height exactly"""
        _need(self, WIDTHS)
        r, bad, fits, scrolls = _measure(), [], 0, 0
        for key, b in sorted(r.items()):
            if not key.startswith("tight "):
                continue
            self.assertNotIn("err", b, "%s: %s" % (key, b))
            if b["sh"] <= b["ch"] + 1:
                fits += 1
                band = b["win"][1] - b["cb"] - b["pb"]
                if band > BAND_TOL:
                    bad.append("%s: %.0fpx of empty band under the content, inside the window (it ends at %.0f of the glass's %.0f)"
                               % (key, band, b["win"][1], b["vh"]))
                if not b["stack"] and None not in (b["left"], b["notes"], b["stats"]):
                    cols = max(b["left"], b["notes"])
                    if abs(b["stats"] - cols) > BAND_TOL:
                        bad.append("%s: STATS ends at %.0f and the columns beside it at %.0f" % (key, b["stats"], cols))
            else:
                scrolls += 1
                if abs((b["win"][1] - b["win"][0]) - b["vh"]) > 0.5:
                    bad.append("%s: it scrolls inside itself but is %.0fpx tall on a %.0fpx glass" % (key, b["win"][1] - b["win"][0], b["vh"]))
        # #42 - each premise names the viewport that carries it, so it binds wherever that viewport is measured
        self.assertGreaterEqual(fits, 2 if LW.at(AT_2000, _ONLY) else 0, "PREMISE: only %d states fit the glass (2000x1300 plain and worn must)" % fits)
        # v3889 (#132) - the scrolling half's premise was 375x812; measured 11-09 at 1120x628 plain and worn both scroll
        self.assertGreaterEqual(scrolls, 2 if LW.at((1120, 628), _ONLY) else 0, "PREMISE: only %d states scroll (1120x628 plain and worn must)" % scrolls)
        self.assertEqual(bad, [], "the builder is not as tall as what it holds:\n  " + "\n  ".join(bad))

    def test_r2_no_builder_panel_is_stretched_past_what_it_holds(self):
        """REG-1379 (round 2, reproduced on fe817ab7): round 1 filled the band under the builder by stretching STRENGTHS AND
        WEAKNESSES and NOTES (an empty bordered box and an empty textarea at 2000x1300). In columns, plain and worn, at every
        width: each is no taller than its own content (or its min-height floor), measured with every stretch taken away"""
        _need(self, WIDTHS)
        r, bad, seen = _measure(), [], 0
        for key, b in sorted(r.items()):
            if not key.startswith("tight ") or b.get("err") or b.get("stack"):
                continue
            seen += 1
            for name, v in (("STRENGTHS AND WEAKNESSES", b.get("sw")), ("NOTES", b.get("nt"))):
                if not v or v[1] is None:
                    bad.append("%s: %s is not drawn" % (key, name))
                elif v[0] > v[1] + BAND_TOL:
                    bad.append("%s: %s is %.0fpx tall and holds %.0fpx - %.0fpx of empty box" % (key, name, v[0], v[1], v[0] - v[1]))
        cols = 2 * len([w for (w, h) in _W(WIDTHS) if w > 900])      # plain and worn at every column width (#42: measured)
        self.assertGreaterEqual(seen, cols, "PREMISE: only %d of %d column states were measured" % (seen, cols))
        self.assertEqual(bad, [], "a builder panel is stretched past what it holds:\n  " + "\n  ".join(bad))


def _rgba(s):
    """'rgb(3, 3, 3)' / 'rgba(16, 4, 70, 0.4)' -> (r, g, b, a), or None"""
    try:
        v = [float(x) for x in str(s)[str(s).index("(") + 1:str(s).rindex(")")].split(",")]
    except Exception:
        return None     # an unreadable colour is UNKNOWN - the caller reports it, never a 0
    return tuple(v + [1.0]) if len(v) == 3 else (tuple(v) if len(v) == 4 else None)


def _over(top, under):
    """the colour SEEN: `top` (with its alpha) composited over the opaque `under` -> (r, g, b) rounded, or None"""
    if top is None or under is None:
        return None
    a = top[3]
    return tuple(round(top[i] * a + under[i] * (1 - a)) for i in range(3))


# v3889 (#132) - six proofs whose defect showed only at 375x812 (the phone's Edit sheet, its stacked panes, the phone
# header's hint box) left with the phone width: measured at a desktop width they could only stay green
RED_PROOF = [
    {
        "why": "#29(d) round 9 - the Edit window keeps its fixed 750-unit frame again (an empty lower third under a charm)",
        "file": "bible.html",
        "find": "    if (fit){ m.style.height = 'auto'; m.style.maxHeight = Math.round(Math.max(H, vh - top - 8)) + 'px'; }\n",
        "replace": "    if (false){}\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#29(d) round 9 - the Edit window is pulled up over the builder's tabs again (EQUIPMENT hidden at 1280x800)",
        "file": "bible.html",
        "find": "    if (_tr && left < _tr.right && left + W > _tr.left && top < _tr.bottom + 6 && vh - (_tr.bottom + 6) - 8 >= 240){\n",
        "replace": "    if (false){\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "REG-1379 round 2 - the builder is the glass's height again, with an empty band under its columns at 2000x1300",
        "file": "bible.html",
        "find": ".cb-win{bottom:auto;max-height:100vh;max-height:100dvh;",
        "replace": ".cb-win{",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "REG-1379 round 2 - STATS is the glass's height again whatever stands beside it (~270px past the columns at 2000x1300)",
        "file": "bible.html",
        "find": ".cb:not(.cb-stack) .cb-stats{min-height:0;height:auto;max-height:calc(100vh - 30px - 66*var(--u));contain:size;align-self:stretch}\n",
        "replace": ".cb:not(.cb-stack) .cb-stats{min-height:0;height:calc(100vh - 30px - 66*var(--u))}\n",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "REG-1379 round 2 - round 1's fix again: STRENGTHS AND WEAKNESSES and NOTES stretch into the band as empty boxes",
        "file": "bible.html",
        "find": ".cb:not(.cb-stack) .cb-stats{min-height:0;height:auto;max-height:calc(100vh - 30px - 66*var(--u));contain:size;align-self:stretch}\n",
        "replace": ".cb:not(.cb-stack) .cb-stats{min-height:0;height:calc(100vh - 30px - 66*var(--u))}\n.cb:not(.cb-stack){align-items:stretch}\n"
                   ".cb:not(.cb-stack) .cb-body{align-self:stretch}\n.cb:not(.cb-stack) .cb-lc{flex:1 1 auto;align-items:stretch}\n"
                   ".cb:not(.cb-stack) .cb-left > :last-child,.cb:not(.cb-stack) .cb-mc > .cb-notes{flex-grow:1}\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "REG-1376 round 2 - the cap sits on the number's line again and widens the value: a label beside it wraps once more",
        "file": "bible.html",
        "find": ".cb-sv:has(> em.cb-cap)",
        "replace": ".cb-sv:has(> em.cb-law-off)",
        "matches": 4,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B4 fix round - a unique's inventory tile is filled gold with a gold frame again (theirs: one indigo)",
        "file": "bible.html",
        "find": ".cb-it.cb-sel{background:rgba(6,98,8,.26)}\n",
        "replace": ".cb-it[data-q=\"u\"]{background:rgba(199,179,119,.12);border-color:rgba(199,179,119,.45)}\n.cb-it.cb-sel{background:rgba(6,98,8,.26)}\n",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 fix round - the art component's rarity bloom is back on an inventory tile (a gold halo round a unique)",
        "file": "bible.html",
        "find": ".cb-it .d2art-wrap .d2art-img{filter:none !important}\n",
        "replace": "",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 fix round - the tile being edited is not green (theirs is the only non-indigo tile)",
        "file": "bible.html",
        "find": "      h += '<div class=\"cb-it' + (sel ? ' cb-sel' : '') +",
        "replace": "      h += '<div class=\"cb-it' +",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 fix round - a charm above the build's level keeps its plain tile (the game turns it red)",
        "file": "bible.html",
        "find": " + (lvlBad || clsBad ? ' cb-red' : '') + ",
        "replace": " + ",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 fix round - the builder stops handing the engine the Required Level: a charm the level cannot use feeds STATS",
        "file": "bible.html",
        "find": "var req = function(e, x, k){ var n = x ? _cbNeedLvl(e, k, b) : 0; if (n) x.lvlreq = n; return x; };",
        "replace": "var req = function(e, x, k){ return x; };",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 fix round - a WORN item above the build's level feeds STATS while its doll slot is red (the sibling)",
        "file": "bible.html",
        "find": "var x = req(s0.slots[k], _cbEngineEntry(s0.slots[k], eng, mine), k);",
        "replace": "var x = _cbEngineEntry(s0.slots[k], eng, mine);",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 fix round - the engine sums an item whose Required Level is above the build's (Annihilus at 50: All Skills 1)",
        "file": "bible.html",
        "find": "        if (lvl !== null && needLvl > lvl){ res.notApplied.push(",
        "replace": "        if (false){ res.notApplied.push(",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 fix round - Calculations lists a red charm's level requirement as met ('none')",
        "file": "bible.html",
        "find": "      if (si === (b.active | 0)) (s.inv || []).forEach(function(e){ var n = _cbNeedLvl(e, 'inv', b); if (n > clvl) fails.push(",
        "replace": "      if (false) (s.inv || []).forEach(function(e){ var n = _cbNeedLvl(e, 'inv', b); if (n > clvl) fails.push(",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B4 - the inventory's 2px gaps come back: the cells are no longer edge to edge like the game's grid",
        "file": "bible.html",
        "find": ".cb-inv{--cb-inv-line:rgb(74,66,60);--cb-inv-cell:rgb(3,3,3);position:relative;margin:0 auto;display:grid;gap:0;padding:0;",
        "replace": ".cb-inv{--cb-inv-line:rgb(74,66,60);--cb-inv-cell:rgb(3,3,3);position:relative;margin:0 auto;display:grid;gap:2px;padding:0;",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B4 - the caption is drawn between the doll and its inventory again (v3514's 'Click a slot ...' line)",
        "file": "bible.html",
        "find": "    return '<div class=\"cb-eqp\" id=\"cb-eqp\">' + doll + inv + '</div>';\n",
        "replace": "    return '<div class=\"cb-eqp\" id=\"cb-eqp\">' + doll + '<div class=\"cb-doll-say\">Click a slot to choose from the entire item database</div>' + inv + '</div>';\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B4 - the inventory escapes the template panel: a separate box under the doll again, not one set",
        "file": "bible.html",
        "find": "    return '<div class=\"cb-eqp\" id=\"cb-eqp\">' + doll + inv + '</div>';\n",
        "replace": "    return '<div class=\"cb-eqp\" id=\"cb-eqp\">' + doll + '</div>' + inv;\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B4 - an item is drawn on the old gapped pitch and drifts out of the cells it occupies",
        "file": "bible.html",
        "find": "    var pitch = L.cell;   /* #174 v-B4",
        "replace": "    var pitch = L.cell + 2;   /* #174 v-B4",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B4 - the grid's cells outgrow the doll: the inventory is wider than the doll it sits under",
        "file": "bible.html",
        "find": "  function _cbCellPx(dk){ return Math.max(12, Math.floor((CB_DOLL_WH[0] * dk - 1) / 10)); }",
        "replace": "  function _cbCellPx(dk){ return Math.max(12, Math.floor((CB_DOLL_WH[0] * dk + 40) / 10)); }",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 round 7 - an inventory pick falls back to the page centre again and covers STATS by 25-28px",
        "file": "bible.html",
        "find": "        if (left + W > _sl){ left = Math.max(8, _sl - W); if (left + W > _sl) W = Math.max(360, _sl - left); }\n",
        "replace": "",
        "matches": 1,
        # #42 measured 2026-09-29: green alone at 1280x800 / 375x812 / 2000x1300; the full sweep is red at 1024x768
        # and 901x900
        "widths": ["1024x768"],
    },
    {
        "why": "#174 round 7 - a Grand Charm is not registered by its base name again: its Edit tile prints its name in a box",
        "file": "bible.html",
        "find": "D2IO_ART['Grand Charm'] = 'art/hd_charm_large.png';",
        "replace": "",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    # #29(a) 2026-09-28 - round 3's sabotage (take the indent's negative margin away) is RETIRED: in the grid row a value has
    # its own column and cannot drop, so that margin carries nothing - measured clean at 375-2000 without it, and it was
    # removed. A sabotage that cannot go red would read as a proof; round 8's two below hold the rule it guarded.
    {
        "why": "#29(a) - the stat row is a wrapping flex line again: a row whose value is wider than the rest drops it ALONE (Fire at 960-1180)",
        "file": "bible.html",
        "find": ".cb-st-r{display:grid;grid-template-columns:1fr auto;align-items:baseline;gap:0 6px;",
        "replace": ".cb-st-r{display:flex;justify-content:space-between;flex-wrap:wrap;align-items:baseline;gap:0 6px;",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    # ⚠ RETIRED 2026-09-28 (v3522 push gate, 22:29): the proof that stood HERE - "a value's RANGE chip and cap may not
    # wrap under its number", which set .cb-sv to flex-wrap:nowrap - was removed because the law stayed GREEN at every
    # width through it - BLIND. (Not the stat-row proof just above: that one turns .cb-st-r from a grid row into a
    # wrapping flex line, goes red, and stands.) Since REG-1376 a CAPPED row is display:block (the cap on its own line),
    # which overrides the flex wrap, and its own proof (".cb-sv:has(> em.cb-cap)" -> off) goes red for it; an
    # UNCAPPED row measured no overflow with nowrap at any of the law's widths, so the wrap is no longer
    # load-bearing. A sabotage of a rule that holds nothing up proves nothing. [[feedback-blind-fixture-green-gate]]
    {
        "why": "#174 round 2 - a wrapped stat label's second line sits flush again ('Resistance' reads as a row with no value)",
        "file": "bible.html",
        "find": ".cb-st-r .cb-sl{min-width:auto;overflow-wrap:normal;padding-left:calc(6*var(--u));text-indent:calc(-6*var(--u))}\n",
        "replace": ".cb-st-r .cb-sl{min-width:auto;overflow-wrap:normal}\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 round 2 - the pointer no longer moves the active option: the row under it is not the one Enter adds",
        "file": "bible.html",
        "find": " onmousemove=\"window._cbModHover(event)\">",
        "replace": ">",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 round 2 - :hover paints a second gold row beside the active one again",
        "file": "bible.html",
        "find": ".cb-add-o:focus-visible{background:rgba(214,170,90,.22);outline:none}",
        "replace": ".cb-add-o:hover,.cb-add-o:focus-visible{background:rgba(214,170,90,.22);outline:none}",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 R2 - the builder's STATS grows with its rows again and runs off the bottom of the window (the Grok seat: rows from Energy down sliced)",
        "file": "bible.html",
        # REG-1379 round 2 moved the rule: STATS is now the columns' height capped by the glass, and it is that rule removed
        "find": ".cb:not(.cb-stack) .cb-stats{min-height:0;height:auto;max-height:calc(100vh - 30px - 66*var(--u));contain:size;align-self:stretch}\n",
        "replace": "",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B3 fix round - the open ADD MOD list keeps a fixed height, below the modal at 1280x800",
        "file": "bible.html",
        "find": "    if (st.modOpen && st.pick) _cbFitAddList();\n",
        "replace": "",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B3 fix round - the active ADD MOD option is not painted (what Enter adds is invisible)",
        "file": "bible.html",
        "find": ".cb-add-o.cb-act{background:rgba(214,170,90,.30);box-shadow:inset 3px 0 0 var(--gold)}",
        "replace": ".cb-add-o.cb-act{}",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B3 fix round - the search box ignores ArrowDown and Enter (ADD MOD is no combobox)",
        "file": "bible.html",
        "find": " onkeydown=\"window._cbModKey(event)\">",
        "replace": ">",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B3 - the open ADD MOD list stops scrolling inside its box and clips its options",
        "file": "bible.html",
        "find": ".cb-add-list{max-height:calc(330*var(--u));min-height:120px;overflow:auto;",
        "replace": ".cb-add-list{max-height:calc(330*var(--u));min-height:120px;overflow:hidden;",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B3 - the Edit tab's controls row (Item level · Quality · Name · Base · Defense · Sockets · Ethereal) "
               "stops wrapping and runs out of the modal on a phone",
        "file": "bible.html",
        "find": ".cb-ctls{display:flex;flex-wrap:wrap;gap:calc(8*var(--u));margin-top:calc(10*var(--u))}",
        "replace": ".cb-ctls{display:flex;flex-wrap:nowrap;gap:calc(8*var(--u));margin-top:calc(10*var(--u))}",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B2 fix round - an active gold button under the pointer paints its label gold on gold again",
        "file": "bible.html",
        "find": ".cb-btn.cb-on:hover:not([disabled]){color:#1a1208;border-color:var(--gold-bright)}",
        "replace": ".cb-btn.cb-on:hover:not([disabled]){border-color:var(--gold-bright)}",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B2 - a prose panel gets a fixed height and clips its words (the class that cut the mule window)",
        "file": "bible.html",
        "find": ".cb-prim{min-height:calc(102*var(--u))}.cb-merc{min-height:calc(80*var(--u))}",
        "replace": ".cb-prim{min-height:calc(102*var(--u))}.cb-merc{height:calc(34*var(--u));overflow:hidden}",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B2 - the modal is centred, so it covers the glowing slot it serves",
        "file": "bible.html",
        "find": "      if (r.right <= cx + 1){ left = r.right + 12; W = Math.min(W0, roomR); }\n      else { W = Math.min(W0, roomL); left = r.left - 12 - W; }\n",
        "replace": "      W = W0; left = (vw - W) / 2;\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B2 - the columns leave their literal 322 | 716",
        "file": "bible.html",
        "find": ".cb-lc{display:grid;grid-template-columns:calc(322*var(--u)) calc(716*var(--u));",
        "replace": ".cb-lc{display:grid;grid-template-columns:calc(360*var(--u)) calc(678*var(--u));",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
]


if __name__ == "__main__":
    if _ONLY is not None:
        sys.stderr.write("⚠ " + LW.banner(_ONLY, VIEWPORTS) + "\n")
    if not os.path.exists(RC.CHROME):
        sys.stderr.write("⚪ SKIP — %s. UNMEASURED, declared as a skip (77), never a pass.\n" % NO_BROWSER)
        raise SystemExit(77)
    unittest.main(verbosity=2)
