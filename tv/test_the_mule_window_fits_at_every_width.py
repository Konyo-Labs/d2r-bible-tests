# -*- coding: utf-8 -*-
"""#174 — THE MULE WINDOW FITS AT EVERY WIDTH, MEASURED IN A REAL BROWSER, NOT READ FROM ITS HTML.

THE DEFECT THIS EXISTS FOR, and why the sibling law could not see it. test_the_mule_window_is_the_planner_shell
drives the shipped openMuleCard in node and reads the HTML it writes. Every panel said what would fill it — the
law checked the words were THERE. On screen, between 900 and 1250 wide, they were not all visible:

    1120x628 (his console width)  the MERCENARY note's last line, the one carrying "(v-C)", cut in half
    1024x768                      "STRENGTHS AND WEAKNESSES" read "TRENGTHS AND WEAKNESSE"; the Stash button
                                  touching the EQUIPMENT title; "Character — none bound…" clipped
    920x800                       the Stash button over the title ("EQUIPMEN"); three notes under their panels
    375x812                       the stash's gold box and the mule tab row scrolling sideways; the header
                                  sub-line ellipsized

Every length in the window was N * --u and the type was fixed px, so the boxes shrank and the words did not.
innerHTML cannot show that: a clipped sentence and a visible one are the same string. Only layout can.
[[visual-regression-detector]] [[regression-guard]] (a presence-law is not a reachability-law)

WHAT IS MEASURED, per width (2000x1300, 1280x800, 1120x628, 1024x768, 901x900, 800x1000, 375x812):
  · no text node in the window is cut by an overflow:hidden/clip ancestor, or lies outside its panel unless it
    is inside a scroller (one scroll away is reachable; cut is destroyed) — and no CONTROL (a tab, a button, a
    slot) has its box sliced by what contains it, words or not
  · nothing in the window scrolls sideways, and the window itself never scrolls sideways
  · no panel header's title runs into its control
  · the window's type is its token times min(1, k), floored at the smallest token (--fs-micro)
  · at 2000x1300 the panels and the ten doll slots are their measured rects (spec §1); at 1280 they are those
    rects times k
#174 v-B2 FIX ROUND, the pixel seat's 375 findings, by real input: a stash item dragged to the top edge scrolls the
window until another mule's tab is reachable, and dropping on it moves the item there (the tabs sat ~1500px above it
and only a wheel turned mid-drag reached them); the keyboard's ] carries an item to the next mule; and on a coarse
pointer a real tap 6px beside a placed ring's 10px lock unlocks it, while the ring's own middle is still the ring.
And once, on a phone (390x844): a keyboard opening (a HEIGHT-only resize) leaves the Stats search box the SAME
node with the caret in it, and a background re-render (an item assigned while it is up) puts the caret back.

#174 v-B — THE SAME QUESTIONS, ASKED AGAIN WITH THE DOLL IN USE. Every width is measured a second time with three
items equipped (a weapon, two rings — worn art, the ✕ controls, stat values with their source tags) and the picker
open on the left hand (its list, its "left out" footer): new words in new boxes are exactly what v-A's pass cannot
see. And the geometry at 2000 is their rects with the ONE declared upgrade (spec §5): the EQUIPMENT body on the
doll's unit, DOLL_K = 1.25 — THEIR_PANELS stays their capture, `_ours()` applies the upgrade to it.

#174 v-B review — THE EQUIP PASS IS REAL INPUT, and THE GOLD BOX IS ONE LINE.
  · The doll is filled the way he fills it: a CDP mouse press and release at the centre of the slot, then at the
    centre of the option — each time checking the point lands on that element (elementFromPoint), so a control
    covered by something else fails here instead of being clicked through by a programmatic .click().
  · "N worn on the doll · M on this mule" wrapped the stash's gold box to two lines at 2000 wide; the stash cell
    budget (_mpLayout) assumes one, so the stash view scrolled 1.5px and cut the box's border. Every width in
    columns now requires the gold box to be one line and the stash view not to scroll, plain and with the doll in use.
  · The worn weapon is Lightsabre (one-handed): beside Windforce the left hand now offers only its quiver, which
    this locker does not hold — an empty picker would measure nothing.

#174 v-B2 — THE LITERAL COLUMNS, THE CONSOLE'S HEIGHT, THE HOVER CARD, AND A REAL DRAG.
  · 2000 is their rects LITERALLY again (DOLL_K = 1: LEFT 322, centre 716 — his "literally the same"); `_ours()` is
    their capture unchanged.
  · 1280x695 joins the widths: his console's board under its own header. The Grok seat on v-B read the bottoms
    "sliced" there — reproduced: the stash panel 64px and PRIMARY SKILLS 37px under the glass. The unit now answers
    the height too, so the header, the mule bar, the doll with its inventory and the stash panel all end inside the
    window, and STATS ends at the window's bottom with its list scrolling inside (at 1280x800 its height is
    min(726k, the room below it)).
  · The hover card of an item on the doll never covers the MULES IN THIS LOCKER band (it read "ES IN THIS LOCKER"):
    hovered with a real mouse move, its top sits at or under the EQUIPMENT header.
    #174 v-B2 integration: that card is now the Character Builder's ONE in-game box, window.d2Tip (#cb-tip) - the
    worn weapon, the worn ring and a stash tile are hovered with a real mouse move at 2000 and at his console's
    1280x695, and each must open #cb-tip naming the hovered item, leave the board's #arttip SHUT (one box, never
    two), keep off the mule bar, and sit at or under the header of the panel its item is in.
  · THE DRAG, WITH REAL INPUT (press, ten moves with the button held, release — never a synthetic event): a ring
    dropped on a cell LOCKS there, the cells it would cover tinted green in the air, and a RELOAD keeps it; a 2x4
    dropped past the grid's edge is tinted red and refused, the store untouched; the keyboard carries an item
    (Enter, arrows, Enter); a right-click unlocks it; a drop on the Gems tab moves an item there; at 1280x695 a ring
    moves from the stash to the inventory and survives a reload. Every target cell is found from the RENDERED cell,
    never from the product's own geometry.

#29(d) his answer 2026-09-28 ("Tighten both") — THE WINDOW IS AS TALL AS WHAT IT HOLDS (REG-1379, round 2). At 2000x1300
their literal rects end at 1052 and the window ran on to the glass's 1300 (248px of empty band; 228 at 901x900). Round 1
stretched the last panel of each column into it, which only moved the emptiness inside: STRENGTHS AND WEAKNESSES ~330px of
empty bordered box, NOTES ~370px of empty textarea. In every arrangement at every width (the doll or the stash in front,
plain and with the doll in use + its picker open): where the window does not scroll it ends under its content by its own
bottom padding and never reaches the glass (no band); where it scrolls it is exactly the glass's height (capped, scrolling
inside); and in columns no panel is stretched past what it holds - STRENGTHS AND WEAKNESSES no taller than its content (or
its 57u floor), NOTES its 206u, STATS its 726u. At 2000 every panel is their rect again, heights included.
REG-1375 (round 2) — THE MULE WINDOW'S OWN TABS STAY IN VIEW WHILE ITS PICKER IS OPEN. The #174 Edit panel lives in the
mule window, and the builder's tab rule skipped the mule host: the Select and Edit modals covered EQUIPMENT / STASH at
every width and the phone sheet covered all four. At every width, the doll and the stash in front, Select (the left hand)
and Edit (a database helm placed through the host's own Select): where the tab row is on the glass with room under it the
modal does not overlap it and each tab's centre hit-tests to that tab.

⚠ ITS OWN BROWSER, ON ITS OWN PORT. A free port is chosen here and exported before render_check is imported,
so this law never adopts a Chrome something else started (REG-1258) and two lanes of heart2 never share one. TV_LAW_PORT
pins one instead (the builder's width law already honoured it) - only for a caller that owns a port range and hands
each concurrent run its own; run_gates and the hook set none.
#42 - A PUSH-TIME RED-PROOF MEASURES ONLY WHERE ITS DEFECT SHOWS (tv/law_widths.py). TV_LAW_WIDTHS, set only by
`heart2.py --push --prove` from a proof's own "widths", restricts every width loop and every one-viewport pass to those
viewports; a case whose viewports are all outside it is a declared SKIP; unset, this law is exactly what it was. The
passes that CHANGE the locker (the equip, the Lacerator assigned under the typing, the drag pass before the phone pass)
still run whenever a later measurement reads what they leave, so a restricted run meets each measured state as the full
run does.
The Chrome it starts is killed by the handle it holds, and its temp profile goes with it.
⚠ NO CHROME ON THIS MACHINE = a DECLARED skip (exit 77), never a pass. Chrome installed and refusing to start is
a FAILURE, not a venue fact.
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
# when the caller owns a port range (parallel builders each given their own), as the builder's width law does - never
# 9222/9223, which are his.
_LAW_PORT = os.environ.get("TV_LAW_PORT", "").strip()
os.environ["TV_RENDER_PORT"] = _LAW_PORT if _LAW_PORT.isdigit() and _LAW_PORT not in ("9222", "9223") else str(_free_port())
import render_check as RC  # noqa: E402
import law_widths as LW  # noqa: E402  #42 - the one reader of TV_LAW_WIDTHS

from test_the_mule_window_is_the_planner_shell import THEIR_SLOTS, DOLL_K, THEIR_EQ  # noqa: E402  ONE witness table

NO_BROWSER = "no Chrome/Chromium on this machine, so the mule window was not rendered"
WIDTHS = ((2000, 1300), (1280, 800), (1280, 695), (1120, 628), (1024, 768), (901, 900), (800, 1000))   # v3889 #132: no 375
CONSOLE = (1280, 695)   # #174 v-B2 — his console's board at 1280 wide, under the console's own header
#: #42 - the one-viewport passes, by the viewports they set: the hover card, the typing under a re-render, the real drag,
#: and the keyboard ] pass. v3889 (#132, his 11-08 "i dont need any mobile anything"): the phone's passes left - a 375 drag
#: held at the top edge, a finger on a placed item's lock, a phone keyboard opening (a height-only resize) - and the typing
#: pass that shared the phone's viewport now types at 1280 (a re-render underneath him is not a phone question)
HOVER_WIDTHS = (WIDTHS[0], CONSOLE)
TYPE_AT = ((1280, 800),)
DRAG_AT = ((2000, 1300), CONSOLE)
KEYS_AT = ((2000, 1300),)
#: every viewport this law measures at - what TV_LAW_WIDTHS may name
VIEWPORTS = tuple(sorted(set(WIDTHS) | set(HOVER_WIDTHS) | set(TYPE_AT) | set(DRAG_AT) | set(KEYS_AT)))
#: #42 - None = every width, exactly as before; run_gates and CI never set it
_ONLY = LW.only()
_W = lambda seq: LW.pick(seq, _ONLY)  # noqa: E731
MULE = "uni-weap"
ITEMS = ["Windforce", "Doombringer", "The Grandfather", "Stormlash", "Lightsabre", "Nagelring", "Raven Frost"]

# their builder at 2000x1300, relative to the content column (spec §1): x, y, w, h
THEIR_PANELS = {
    "mp-set": (0, 98, 1044, 84), "mp-eq": (0, 188, 322, 400), "mp-prim": (0, 594, 322, 102),
    "mp-merc": (0, 702, 322, 80), "mp-loot": (0, 788, 322, 88), "mp-sw": (0, 882, 322, 57),
    "mp-cp": (328, 188, 716, 628), "mp-notes": (328, 822, 716, 206),
    "mp-auth": (1050, 0, 300, 150), "mp-show": (1050, 156, 300, 150), "mp-stats": (1050, 312, 300, 726),
}
TOL_2000 = 4.0          # spec §4: ±4 px at 2000 wide
SW_TOL = 4.0            # S&W is measured off their PNG (182..239), the least exact of the reference numbers
LEFT_PANELS = ("mp-eq", "mp-prim", "mp-merc", "mp-loot", "mp-sw")
CENTRE_PANELS = ("mp-cp", "mp-notes")


def _ours(c):
    """THEIR panel rect on the doll's unit (DOLL_K). #174 v-B2: DOLL_K is 1 — their capture, literally — so this is
    their rect unchanged; it stays parametric so a future declared upgrade moves every dependent rect with it: the
    LEFT column their 322 on the doll's unit, EQUIPMENT their 36px header + 364px body on it, the left panels below
    moving down and the centre moving right by what those grew."""
    x, y, w, h = THEIR_PANELS[c]
    grow_w = 322 * DOLL_K - 322
    grow_h = (THEIR_EQ[0] + THEIR_EQ[1] * DOLL_K) - sum(THEIR_EQ)
    if c in LEFT_PANELS:
        w = 322 * DOLL_K
        if c == "mp-eq":
            h = THEIR_EQ[0] + THEIR_EQ[1] * DOLL_K
        else:
            y += grow_h
    elif c in CENTRE_PANELS:
        x, w = x + grow_w, w - grow_w
    return (x, y, w, h)


def _our_slot(s):
    """their slot rect, on the doll's unit, under their 36px header"""
    x, y, w, h = THEIR_SLOTS[s]
    return (x * DOLL_K, THEIR_EQ[0] + (y - THEIR_EQ[0]) * DOLL_K, w * DOLL_K, h * DOLL_K)

SEED = r"""(function(items, mule){
  try { localStorage.setItem('d2r_ownerClaim','*'); } catch(e){}
  var ok = 0;
  /* REG-2697 (v3815/v3816 CI): a bare tvVaultRegister is refused while AUTO INTAKE is off (v3767's register stop), so this
     seed only ever filed through vaultAssign owning the name as a side effect - the #148.4 defect v3815 closed. His hand
     door adds it (answering the name it filed under), then it is filed. */
  items.forEach(function(n){ try { var h = window.vaultHandAdd(n); window.vaultAssign((h && h.name) || n, mule); ok++; } catch(e){} });
  return ok; })(%s, %s)"""

MEASURE = r"""(function(){ try {
  var d = document, box = d.getElementById('vault-detail'), mp = box && box.querySelector('.mp');
  if (!mp) return JSON.stringify({ err: 'the mule window did not render (.mp absent)' });
  var ob = mp.getBoundingClientRect();
  var rel = function(el, b){ if (!el) return null; var r = el.getBoundingClientRect(); b = b || ob;
    return [r.left - b.left, r.top - b.top, r.width, r.height]; };
  var sv = box.querySelector('.mp-cp .mp-view:not([hidden])'), gb = sv && sv.querySelector('.vd-goldbox'), gl = null;
  if (gb && sv && !sv.hidden){ var gs = getComputedStyle(gb), gr = gb.getBoundingClientRect();
    gl = (gr.height - parseFloat(gs.paddingTop) - parseFloat(gs.paddingBottom) - parseFloat(gs.borderTopWidth) - parseFloat(gs.borderBottomWidth)) / parseFloat(gs.lineHeight); }
  var out = { k: +mp.getAttribute('data-k'), goldLines: gl, goldText: gb ? gb.textContent : null, mpTop: ob.top, vh: innerHeight,
    vscroll: [box.scrollHeight, box.clientHeight], padB: parseFloat(getComputedStyle(box).paddingBottom) || 0,
    stashScroll: (sv && !sv.hidden) ? [sv.scrollHeight, sv.clientHeight] : null,
    stack: mp.classList.contains('mp-stack'), hscroll: [box.scrollWidth, box.clientWidth], panels: {}, slots: {},
    cut: [], outside: [], sideways: [], collide: [], nText: 0,
    worn: box.querySelectorAll('.mp-slot.mp-has').length, sv: box.querySelectorAll('.mp-sv').length,
    pick: box.querySelectorAll('.mp-pick').length, opts: box.querySelectorAll('.mp-pick .mp-opt').length };
  out.front = (box.querySelector('.mp-ctab.on') || {}).getAttribute ? box.querySelector('.mp-ctab.on').getAttribute('data-view') : null;
  ['mp-set','mp-eq','mp-sstash','mp-prim','mp-merc','mp-loot','mp-sw','mp-cp','mp-notes','mp-auth','mp-show','mp-stats'].forEach(function(c){
    out.panels[c] = rel(box.querySelector('.' + c)); });
  var eo = box.querySelector('.mp-eq').getBoundingClientRect();
  [].forEach.call(box.querySelectorAll('.mp-slot'), function(s){ out.slots[s.getAttribute('data-slot')] = rel(s, eo); });
  var root = getComputedStyle(d.documentElement);
  out.tokens = { title: parseFloat(root.getPropertyValue('--fs-title')), meta: parseFloat(root.getPropertyValue('--fs-meta')),
                 micro: parseFloat(root.getPropertyValue('--fs-micro')) };
  var ht = box.querySelector('.mp-h-t'), em = box.querySelector('.mp-left .mp-empty');
  out.fs = { title: ht ? parseFloat(getComputedStyle(ht).fontSize) : null, meta: em ? parseFloat(getComputedStyle(em).fontSize) : null };
  /* every visible text node: the first ancestor that does not show overflow decides its fate */
  var tw = d.createTreeWalker(mp, NodeFilter.SHOW_TEXT), n;
  while ((n = tw.nextNode())){
    var t = n.textContent.trim(); if (!t) continue;
    var el = n.parentElement; if (el.closest('[hidden]')) continue;
    /* an item TILE clips its own art by design — a 1x1 ring is one grid cell, and when the art file is absent
       (a sandbox has no art/) its fallback glyph is art too, read by its tooltip. Prose is what must not be cut. */
    if (el.closest('.vd-item')) continue;
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
      var ar = a.getBoundingClientRect(), cl = ar.left + a.clientLeft, ct = ar.top + a.clientTop,
          cr = cl + a.clientWidth, cb = ct + a.clientHeight;
      var hx = (L < cl - 0.5 || R > cr + 0.5), hy = (T < ct - 0.5 || B > cb + 0.5);
      var hid = function(o){ return o === 'hidden' || o === 'clip'; };
      if ((hx && hid(s.overflowX)) || (hy && hid(s.overflowY)))
        out.cut.push(String(a.className).slice(0, 30) + ' cuts "' + t.slice(0, 48) + '"'
          + (hx ? ' by ' + Math.max(cl - L, R - cr).toFixed(1) + 'px across' : '') + (hy ? ' by ' + Math.max(ct - T, B - cb).toFixed(1) + 'px down' : ''));
      scrolled = !hid(s.overflowX) || !hid(s.overflowY);
      break;
    }
    var p = el.closest('.mp-p');
    if (p && !scrolled){ var pr = p.getBoundingClientRect();
      if (B > pr.bottom + 0.5 || R > pr.right + 0.5 || L < pr.left - 0.5)
        out.outside.push('"' + t.slice(0, 40) + '" outside ' + String(p.className).replace('mp-p ', '')); }
  }
  /* a CONTROL cut by its container is the same defect with no words in it: a tab whose right edge is sliced off
     reads as a broken tab even when its label survives. Its whole border box must be inside what clips it. */
  [].forEach.call(mp.querySelectorAll('button,[onclick],.mp-settab,.mp-slot,.mp-box,.mp-cls,.mp-search'), function(e){
    if (e.closest('.vd-item') || e.closest('[hidden]')) return;
    var r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return;
    for (var a = e.parentElement; a && a !== box; a = a.parentElement){
      var s = getComputedStyle(a); if (s.overflowX === 'visible' && s.overflowY === 'visible') continue;
      var hid = function(o){ return o === 'hidden' || o === 'clip'; };
      var ar = a.getBoundingClientRect(), cl = ar.left + a.clientLeft, ct = ar.top + a.clientTop,
          cr = cl + a.clientWidth, cb = ct + a.clientHeight;
      var dx = Math.max(cl - r.left, r.right - cr), dy = Math.max(ct - r.top, r.bottom - cb);
      if ((dx > 0.5 && hid(s.overflowX)) || (dy > 0.5 && hid(s.overflowY)))
        out.cut.push(String(a.className).slice(0, 30) + ' cuts the control ' + String(e.className || e.tagName).slice(0, 34)
          + ' "' + (e.textContent || '').trim().slice(0, 30) + '" by ' + Math.max(dx, dy).toFixed(1) + 'px');
      break;
    }
  });
  [].forEach.call(mp.querySelectorAll('*'), function(e){ var s = getComputedStyle(e);
    if ((s.overflowX === 'auto' || s.overflowX === 'scroll') && e.scrollWidth > e.clientWidth + 1)
      out.sideways.push(String(e.className).slice(0, 30) + ' ' + e.scrollWidth + '/' + e.clientWidth); });
  /* the title is its own span, or — on markup that lost it — the header's first words; either way it is ink */
  [].forEach.call(box.querySelectorAll('.mp-h'), function(h){
    var c = h.querySelector('.mp-h-r'); if (!c || !c.firstElementChild) return;
    var t = h.querySelector('.mp-h-t');
    if (!t) for (var x = h.firstChild; x; x = x.nextSibling) if (x.nodeType === 3 && x.textContent.trim()){ t = x; break; }
    if (!t) return;
    var rg = d.createRange(); rg.selectNodeContents(t); var tr = rg.getBoundingClientRect(), cr = c.getBoundingClientRect();
    if (tr.right > cr.left + 0.5 && tr.bottom > cr.top && tr.top < cr.bottom)
      out.collide.push('"' + t.textContent.trim() + '" runs ' + (tr.right - cr.left).toFixed(1) + 'px under its control'); });
  return JSON.stringify(out);
 } catch(e){ return JSON.stringify({ err: String(e) }); } })()"""

#: #174 v-B review — equip through the window's own picker with REAL INPUT: the centre of an element, scrolled into
#: view, is hit-tested (elementFromPoint must be that element or inside it) and then pressed with CDP mouse events.
#: A programmatic .click() skips hit-testing, so a covered or clipped control would be "clicked" anyway.
AIM = r"""(function(sel, i){ var e = document.querySelectorAll(sel)[i]; if (!e) return JSON.stringify(null);
  e.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' }); var r = e.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
  var at = document.elementFromPoint(x, y); return JSON.stringify({ x: x, y: y, hit: !!(at && (at === e || e.contains(at))) }); })(%s, %d)"""
OPT_AT = r"""(function(want){ var o = document.querySelectorAll('#vault-detail .mp-pick .mp-opt');
  for (var i = 0; i < o.length; i++) if ((o[i].textContent || '').indexOf(want) >= 0) return i; return -1; })(%s)"""
WEAR = [["rarm", "Lightsabre"], ["rrin", "Nagelring"], ["lrin", "Raven Frost"]]


def _press(t, sel, i=0):
    """a real mouse press + release at the centre of sel[i] -> None, or why it could not be pressed"""
    a = json.loads(t.ev(AIM % (json.dumps(sel), i)))
    if not a:
        return "no %s[%d] on the page" % (sel, i)
    if not a["hit"]:
        return "the centre of %s[%d] is covered by another element" % (sel, i)
    for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
        t.send("Input.dispatchMouseEvent", type=kind, x=a["x"], y=a["y"], button="none" if kind == "mouseMoved" else "left",
               clickCount=0 if kind == "mouseMoved" else 1)
    time.sleep(0.2)
    return None


def _equip(t, mule, want):
    """open the picker on each slot and choose the item, by real input -> [names equipped] + [why not]"""
    t.ev("(function(){ window.vaultCloseCard(); window.openMuleCard(%s); return 1; })()" % json.dumps(mule))
    time.sleep(0.3)
    got = []
    for slot, name in want:
        why = _press(t, '#vault-detail .mp-slot[data-slot="%s"]' % slot)
        if why:
            got.append("NOT PRESSED: " + why)
            continue
        i = t.ev(OPT_AT % json.dumps(name))
        why = ("%s was not offered for the %s" % (name, slot)) if i is None or i < 0 else _press(t, "#vault-detail .mp-pick .mp-opt", i)
        got.append(("NOT CHOSEN: " + why) if why else name)
    return got

#: #174 v-B2 — the hover card of an item, against the mule bar and the header of the panel the item is in.
#: #174 v-B2 integration: the card is window.d2Tip's box (#cb-tip); the board's #arttip must stay shut (one box)
HOVER = r"""(function(sel){ var t = document.getElementById('cb-tip'), at = document.getElementById('arttip'),
      s = document.querySelector('#vault-detail .mp-set'), a = document.querySelector(sel), p = a && a.closest('.mp-p'), h = null,
      w = a && (a.querySelector('.d2art-wrap[aria-label]') || a);
  /* #174 R1 — the big doll panel has no header; its floor is the nearest panel header above it (the centre's tabs) */
  while (p && !(h = p.querySelector('.mp-h, .mp-ctabs'))) p = p.parentElement && p.parentElement.closest('.mp-p');
  if (!s || !a || !h) return JSON.stringify({ err: 'no mule bar, hovered item or panel header on the page (' + sel + ')' });
  if (!t) return JSON.stringify({ on: false, err: 'the in-game box (#cb-tip) was never created - no hover opened it' });
  var cs = getComputedStyle(t), r = t.getBoundingClientRect(), b = s.getBoundingClientRect(), first = t.firstElementChild;
  return JSON.stringify({ on: !t.hidden && cs.display !== 'none' && r.height > 0, name: first ? first.textContent : null,
    want: w.getAttribute('aria-label'), arttip: !!(at && at.classList.contains('on')),
    tip: [r.left, r.top, r.right, r.bottom], bar: [b.left, b.top, b.right, b.bottom], headBottom: h.getBoundingClientRect().bottom,
    overBar: !(r.right <= b.left || r.left >= b.right || r.bottom <= b.top || r.top >= b.bottom) }); })(%s)"""
#: the hovered items: the worn right-hand weapon; the worn right RING, whose short box fits ABOVE it and would cross
#: the EQUIPMENT header and the mule bar if the floor were gone (a weapon's tall box never fits above anything near
#: the top, so it goes below on its own and cannot tell the floor from no floor - measured: 470px at 1280x695); and
#: a stash tile (the smallest, top-most), so a grid tile is proven to open the same box. Each named by an attribute
#: the render gives it, found fresh.
HOVER_AT = (("weapon", '#vault-detail .mp-slot[data-slot="rarm"]'),
            ("ring", '#vault-detail .mp-slot[data-slot="rrin"]'),
            ("stash", None))
TOPLEFT = r"""(function(){ var g = document.querySelector('#vault-detail .mp-v-stash .vd-grid[data-area]'); if (!g) return 'null';
  var n = function(e, a){ return +e.getAttribute(a); };
  var it = [].slice.call(g.querySelectorAll('.vd-item[data-fk]')).sort(function(a, b){ return (n(a, 'data-w') * n(a, 'data-h') - n(b, 'data-w') * n(b, 'data-h')) || (n(a, 'data-y') - n(b, 'data-y')) || (n(a, 'data-x') - n(b, 'data-x')); })[0];
  return JSON.stringify(it ? '#vault-detail .vd-item[data-fk="' + it.getAttribute('data-fk') + '"]' : null); })()"""


def _hover_worn(t, view="equip"):
    """open the window, park the pointer, then a REAL mouse move onto each item's art; returns {what: probe}.
    #174 R1 — in BOTH arrangements: with the stash in front the doll is the small card at the top-left, right under
    the mule bar, which is where a floorless box rises over the bar (the case this was written for); with the doll in
    front it is big in the centre, under the tab band."""
    out = {}
    for what, sel in HOVER_AT:
        _open(t, view)
        if sel is None:
            sel = json.loads(t.ev(TOPLEFT))
            if not sel:
                out[what] = {"err": "the stash has no tile to hover"}
                continue
        t.send("Input.dispatchMouseEvent", type="mouseMoved", x=2, y=2, button="none")
        time.sleep(0.3)
        r = json.loads(t.ev("(function(){ var a = document.querySelector(%s), e = a && (a.querySelector('.d2art-wrap[aria-label]') || a);"
                            " if (!e) return 'null'; e.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });"
                            " var r = e.getBoundingClientRect(); return JSON.stringify([r.left + r.width / 2, r.top + r.height / 2]); })()"
                            % json.dumps(sel)))
        if not r:
            out[what] = {"err": "no art anchor for %s" % sel}
            continue
        t.send("Input.dispatchMouseEvent", type="mouseMoved", x=r[0], y=r[1], button="none")
        time.sleep(0.7)
        out[what] = json.loads(t.ev(HOVER % json.dumps(sel)))
        t.send("Input.dispatchMouseEvent", type="mouseMoved", x=2, y=2, button="none")
        time.sleep(0.2)
    return out


#: #174 v-B2 — the drag pass. A tile by (part of) its key: where it sits, whether it is locked, and whether its centre
#: is really the tile (elementFromPoint), so a covered item fails instead of being pressed through
TILE = r"""(function(k){ var e = [].filter.call(document.querySelectorAll('#vault-detail .vd-item[data-key]'), function(e){ return e.getAttribute('data-key').indexOf(k) >= 0; })[0];
  if (!e) return JSON.stringify(null);
  e.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
  var g = e.closest('.vd-grid'), r = e.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2, at = document.elementFromPoint(x, y);
  return JSON.stringify({ key: e.getAttribute('data-key'), area: g.getAttribute('data-area'), x: +e.getAttribute('data-x'), y: +e.getAttribute('data-y'),
    held: e.classList.contains('vd-held'), cx: x, cy: y, hit: !!(at && (at === e || e.contains(at))),
    lock: !!(at && at.closest && at.closest('.vd-unlock')) }); })(%s)"""
#: the centre of the RENDERED cell (x, y) of a grid — found from the cell element itself, never from the product's geometry
CELL_AT = r"""(function(area, x, y){ var g = document.querySelector('#vault-detail .vd-grid[data-area="' + area + '"]'); if (!g) return 'null';
  var c = g.querySelectorAll('.vd-cell')[y * (+g.getAttribute('data-gw')) + x]; if (!c) return 'null';
  var r = c.getBoundingClientRect(); return JSON.stringify([r.left + r.width / 2, r.top + r.height / 2]); })(%s, %d, %d)"""
MID = r"""JSON.stringify({ drop: (document.querySelector('#vault-detail .vd-drop') || {}).className || null, ghost: !!document.querySelector('.vd-ghost') })"""
POS = r"""(function(){ try { return JSON.stringify(JSON.parse(window.LSR.getItem('d2r_mulePos') || '{}')[%s] || {}); } catch (e){ return '{}'; } })()"""


#: #174 R1 — open a mule with a named view in front: "equip" (the doll + inventory big in the centre, the stash small at
#: the left — what a mule opens on) or "stash" (the v3506 arrangement, their builder's geometry). A choice is remembered
#: per mule, so every open says which one it wants rather than inheriting the last.
OPEN_AS = r"""(function(m, v){ window.vaultCloseCard(); window.openMuleCard(m);
  if (v && window._mpViewFor && window._mpViewFor(m) !== v) window._mpSet('view', v);
  var b = document.getElementById('vault-detail'); if (b) b.scrollTop = 0; return 1; })(%s, %s)"""


def _open(t, view="equip", mule=None):
    t.ev(OPEN_AS % (json.dumps(mule or MULE), json.dumps(view)))
    time.sleep(0.35)
    # ⚠ 2026-09-29 — THE FONT WAIT AT BOOT IS NOT ENOUGH. A face is only fetched when a view first USES it, so the
    # stash-in-front view can start a font load the moment it opens, after the one wait in _measure() said "loaded".
    # MEASURED: the v3523 pre-flight read 'st 2000x1300 mp-eq' 6 px low (194 vs 188) inside a 39-min gate run under
    # load, and exact when the law ran alone - the same 6 px on the same panel as the v3513 CI flake above. Bounded (5 s).
    for _ in range(20):
        try:
            if t.ev("document.fonts.status") == "loaded":
                break
        except Exception:
            pass
        time.sleep(0.25)
    # fonts.status can already say loaded on the first look, one frame before the stash
    # face reflows the equipment panel. v3645 and v3646 both measured mp-eq at y=194
    # against the pin 188, which is the miss this wait was added for. Two matching
    # reads means the panel has stopped moving. A stable 194 still fails the pin.
    last = None
    for _ in range(12):
        try:
            top = t.ev("((document.querySelector('.mp-eq')||{}).getBoundingClientRect()||{}).top")
        except Exception:
            top = None
        if last is not None and top == last:
            break
        last = top
        time.sleep(0.25)


def _tile(t, k):
    return json.loads(t.ev(TILE % json.dumps(k)))


def _real_drag(t, a, b, mid_js=MID):
    """press, ten moves with the left button held, release — the real drag, as the pointer does it"""
    t.send("Input.dispatchMouseEvent", type="mouseMoved", x=a[0], y=a[1], button="none", buttons=0)
    t.send("Input.dispatchMouseEvent", type="mousePressed", x=a[0], y=a[1], button="left", buttons=1, clickCount=1)
    for i in range(1, 11):
        t.send("Input.dispatchMouseEvent", type="mouseMoved", x=a[0] + (b[0] - a[0]) * i / 10.0,
               y=a[1] + (b[1] - a[1]) * i / 10.0, button="left", buttons=1)
        time.sleep(0.03)
    seen = t.ev(mid_js)
    seen = json.loads(seen) if isinstance(seen, str) else seen
    t.send("Input.dispatchMouseEvent", type="mouseReleased", x=b[0], y=b[1], button="left", buttons=0, clickCount=1)
    time.sleep(0.45)
    return seen


def _key(t, key, vk):
    for kind in ("keyDown", "keyUp"):
        p = dict(type=kind, key=key, code=key, windowsVirtualKeyCode=vk, nativeVirtualKeyCode=vk)
        if kind == "keyDown" and key == "Enter":
            p["text"] = "\r"
        t.send("Input.dispatchKeyEvent", **p)
    time.sleep(0.25)


def _reload(t, bible):
    t.send("Page.navigate", url="file://" + bible)
    for _ in range(160):
        time.sleep(0.25)
        try:
            if t.ev("(function(){try{return !!(window.openMuleCard&&window.vaultAssign&&window.tvVaultRegister&&window._mpLayout)}catch(e){return false}})()") is True:
                return True
        except Exception:
            pass
    return False


def _drag_pass(t, bible):
    """THE DRAG, with real input, in the owner's world (reloaded first: the claim is set after the first load, so a
    reload is the only way the spots are read back from the world they were written to)"""
    out = {}
    if not _reload(t, bible):
        return {"err": "bible.html did not come back after a reload - UNKNOWN, not passing"}
    time.sleep(0.4)
    out["seeded"] = t.ev(SEED % (json.dumps(ITEMS + ["The Stone of Jordan"]), json.dumps(MULE)))
    for label, (w, h), want in (("2000", (2000, 1300), ("personal", 9, 9)), ("console", CONSOLE, ("inv", 9, 3))):
        t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
        time.sleep(0.25)
        # #174 R1 — at 2000 the drag runs with the doll in front (the side stash); in the console it lands in the SMALL
        # inventory (the stash in front) - a 22px cell is where a corner lock can reach a ring's middle
        view = "stash" if label == "console" else "equip"
        _open(t, view)
        d = {"want": list(want), "from": _tile(t, "Jordan"), "view": view}
        b = json.loads(t.ev(CELL_AT % (json.dumps(want[0]), want[1], want[2])))
        if d["from"] and d["from"]["hit"] and b:
            d["mid"] = _real_drag(t, (d["from"]["cx"], d["from"]["cy"]), b)
        d["after"] = _tile(t, "Jordan")
        d["store"] = json.loads(t.ev(POS % json.dumps(MULE))).get(d["from"]["key"] if d["from"] else "", {})
        _reload(t, bible)
        time.sleep(0.3)
        _open(t, view)
        d["reloaded"] = _tile(t, "Jordan")
        out[label] = d
        if label != "2000":
            continue
        # a 2x4 pulled past the grid's right edge: red in the air, refused, nothing written
        f = {"from": _tile(t, "Windforce")}
        c = json.loads(t.ev(CELL_AT % (json.dumps(f["from"]["area"] if f["from"] else "personal"), 9, 1)))
        if f["from"] and f["from"]["hit"] and c:
            f["mid"] = _real_drag(t, (f["from"]["cx"], f["from"]["cy"]), c)
        f["after"] = _tile(t, "Windforce")
        f["store"] = json.loads(t.ev(POS % json.dumps(MULE)))
        f["said"] = json.loads(t.ev("JSON.stringify(window._mpSaid || null)"))
        out["refuse"] = f
        # the keyboard: focus the ring, Enter, Left, Up, Enter
        _open(t)
        k = {"focused": t.ev("(function(){ var e = [].filter.call(document.querySelectorAll('#vault-detail .vd-item[data-key]'), function(e){ return e.getAttribute('data-key').indexOf('Jordan') >= 0; })[0];"
                             " if (!e) return false; e.focus(); return document.activeElement === e; })()")}
        _key(t, "Enter", 13)
        k["carry"] = json.loads(t.ev(MID))["drop"]
        _key(t, "ArrowLeft", 37)
        _key(t, "ArrowUp", 38)
        _key(t, "Enter", 13)
        time.sleep(0.2)
        k["after"] = _tile(t, "Jordan")
        k["open"] = t.ev("!document.getElementById('vault-detail').hidden")
        out["keys"] = k
        # a right-click on the placed ring: back to auto-pack
        u = _tile(t, "Jordan")
        if u:
            t.send("Input.dispatchMouseEvent", type="mouseMoved", x=u["cx"], y=u["cy"], button="none")
            t.send("Input.dispatchMouseEvent", type="mousePressed", x=u["cx"], y=u["cy"], button="right", buttons=2, clickCount=1)
            t.send("Input.dispatchMouseEvent", type="mouseReleased", x=u["cx"], y=u["cy"], button="right", buttons=0, clickCount=1)
            time.sleep(0.4)
        out["unlock"] = {"after": _tile(t, "Jordan"), "store": json.loads(t.ev(POS % json.dumps(MULE)))}
        # a drop on the Gems tab
        g = {"from": _tile(t, "Nagelring")}
        tb = json.loads(t.ev("(function(){ var e = document.querySelector('#vault-detail .mp-v-stash .vd-tab[data-tab=\"gems\"]'); if (!e) return 'null';"
                             " var r = e.getBoundingClientRect(); return JSON.stringify([r.left + r.width / 2, r.top + r.height / 2]); })()"))
        if g["from"] and g["from"]["hit"] and tb:
            g["over"] = _real_drag(t, (g["from"]["cx"], g["from"]["cy"]), tb,
                                   "!!document.querySelector('#vault-detail .vd-tab[data-tab=\"gems\"].vd-over')")
        g["after"] = _tile(t, "Nagelring")
        out["gems"] = g
    return out


#: #174 v-B2 fix round - a locker big enough to spill onto a second mule: the board's own unique body armors (2x3)
BIG = "uni-armor"
BIG_SEED = r"""(function(mule){
  try { localStorage.setItem('d2r_ownerClaim','*'); } catch(e){}
  var names = Object.keys(ITEM_CODEX).filter(function(n){ var c = ITEM_CODEX[n] || {}; return c.rarity === 'unique'
    && /Plate|Mail|Armor|Coat|Hauberk|Robe|Shell|Cuirass|Breast|Jacket|Leather|Wyrmhide|Scarab|Serpent/i.test(c.base || ''); }).sort().slice(0, 34);
  var ok = 0; names.forEach(function(n){ try { var h = window.vaultHandAdd(n); window.vaultAssign((h && h.name) || n, mule); ok++; } catch(e){} });
  return JSON.stringify(ok); })(%s)"""
FIRST_STASH_KEY = r"""(function(){ var g = document.querySelector('#vault-detail .vd-grid[data-area="personal"][data-page="0"]');
  var e = g && g.querySelector('.vd-item[data-key]'); return e ? e.getAttribute('data-key') : null; })()"""
RECT = r"""(function(sel){ var e = document.querySelector(sel); if (!e) return 'null'; var r = e.getBoundingClientRect();
  return JSON.stringify([r.left + r.width / 2, r.top + r.height / 2, r.left, r.top, r.right, r.bottom]); })(%s)"""
SCROLL = "document.getElementById('vault-detail').scrollTop"
PAGE_OF = r"""(function(mule, k){ try { var p = (JSON.parse(window.LSR.getItem('d2r_mulePos') || '{}')[mule] || {})[k]; return p ? p.page : null; } catch (e){ return null; } })(%s, %s)"""


def _keys_pass(t):
    """#174 v-B2 fix round - a keyboard had no key that changes mule: ] carries a stash item to the next mule's tab and
    Enter moves it there, by REAL keys at 2000. v3889 (#132): the two 375 passes that shared this one (a drag held at the
    window's top edge, a finger on a placed item's lock) left with the phone page."""
    out = {"seed": t.ev(BIG_SEED % json.dumps(BIG))}
    # the keyboard: ] carries a stash item to the next mule, Enter moves it there
    t.send("Emulation.setDeviceMetricsOverride", width=2000, height=1300, deviceScaleFactor=1, mobile=False)
    time.sleep(0.3)
    t.ev("(function(){ window.vaultCloseCard(); window.openMuleCard(%s); window._muleSetPage(0); return 1; })()" % json.dumps(BIG))
    time.sleep(0.4)
    k2 = t.ev(FIRST_STASH_KEY)
    kb = {"key": k2, "focused": t.ev("(function(k){ var e = [].filter.call(document.querySelectorAll('#vault-detail .vd-item[data-key]'), function(e){ return e.getAttribute('data-key') === k; })[0];"
                                     " if (!e) return false; e.focus(); return document.activeElement === e; })(%s)" % json.dumps(k2))}
    _key(t, "Enter", 13)
    _key(t, "]", 221)
    kb["over"] = t.ev("!!document.querySelector('#vault-detail .mp-settab[data-page=\"1\"].vd-over')")
    kb["said"] = json.loads(t.ev("JSON.stringify(window._mpSaid || null)"))
    _key(t, "Enter", 13)
    time.sleep(0.3)
    kb["page"] = t.ev(PAGE_OF % (json.dumps(BIG), json.dumps(k2)))
    out["keys"] = kb
    return out


#: REG-1379 round 2 - the WINDOW (#vault-detail) against what it holds, and the natural height of STRENGTHS AND WEAKNESSES:
#: its own content (or its min-height floor) with every stretch taken away, measured by sizing it to max-content in place
TIGHT = r"""(function(){ var box = document.getElementById('vault-detail'), mp = box && box.querySelector('.mp');
  if (!mp) return JSON.stringify({ err: 'the mule window did not render (.mp absent)' });
  var br = box.getBoundingClientRect(), mr = mp.getBoundingClientRect(), bs = getComputedStyle(box);
  var natural = function(e){ if (!e) return null; var s = e.style;
    s.setProperty('height', 'max-content', 'important'); s.setProperty('flex', 'none', 'important'); s.setProperty('align-self', 'flex-start', 'important');
    var h = e.getBoundingClientRect().height; s.removeProperty('height'); s.removeProperty('flex'); s.removeProperty('align-self'); return h; };
  var sw = box.querySelector('.mp-sw'), h = function(c){ var e = box.querySelector(c); return e ? e.getBoundingClientRect().height : null; };
  return JSON.stringify({ win: [br.top, br.bottom], mp: [mr.top, mr.bottom], vh: innerHeight, sh: box.scrollHeight, ch: box.clientHeight,
    padB: parseFloat(bs.paddingBottom) || 0, stack: mp.classList.contains('mp-stack'), k: +mp.getAttribute('data-k'),
    sw: h('.mp-sw'), swNat: natural(sw), notes: h('.mp-notes'), stats: h('.mp-stats') }); })()"""
#: REG-1375 round 2 - the mule window's own tab row while the modal is open: overlapped or not, each tab's centre hit-tested
MTABS = r"""(function(){ var m = document.getElementById('cb-modal'), tb = document.querySelector('#vault-detail .mp-ctabs');
  if (!m || m.hidden) return JSON.stringify({ modal: false });
  if (!tb) return JSON.stringify({ modal: true, err: 'the mule tab row (.mp-ctabs) is not drawn' });
  var mr = m.getBoundingClientRect(), tr = tb.getBoundingClientRect(), vh = innerHeight;
  var hit = [].map.call(tb.querySelectorAll('.mp-ctab'), function(b){ var r = b.getBoundingClientRect(), x = r.left + r.width / 2, y = r.top + r.height / 2;
    var at = (y >= 0 && y < vh) ? document.elementFromPoint(x, y) : null; return { tab: b.textContent.trim(), seen: !!(at && (at === b || b.contains(at))) }; });
  return JSON.stringify({ modal: true, tab: ((m.querySelector('.cb-tab.cb-on') || {}).textContent || '').trim(), edit: !!m.querySelector('.cb-ed'),
    onScreen: tr.height > 0 && tr.bottom > 0 && tr.top < vh, room: vh - tr.bottom, hit: hit,
    over: mr.left < tr.right && mr.right > tr.left && mr.top < tr.bottom && mr.bottom > tr.top,
    tabs: [tr.left, tr.top, tr.width, tr.height], at: [mr.left, mr.top, mr.width, mr.height] }); })()"""
#: a DATABASE helm on the doll through the host's own Select (a locker item opens on its list, a database item on Edit)
HELM = r"""(function(mule){ window.vaultCloseCard(); window.openMuleCard(mule); window._mpPick('head'); window._cbPickTab('select');
  var r = window._cbPickRows().filter(function(x){ return x[1] === 'Crown of Ages'; })[0];
  if (!r) { window._mpPick(null); return 'Crown of Ages is not in the Select list'; }
  window._cbChoose(r[0]); window._mpPick(null); return r[0]; })(%s)"""
UNHELM = "(function(){ window._mpPick('head'); window._cbUnequip(); window._mpPick(null); return 1; })()"

FOCUS_TYPE = r"""(function(){ var i = document.querySelector('#vault-detail .mp-search input'); if (!i) return 'no search box';
  i.focus(); i.value = 'fire'; window._mpFilter('fire'); i.setSelectionRange(2, 3); window.__mpBox = i;
  return document.activeElement === i ? 'typing' : 'focus refused'; })()"""
FOCUS_READ = r"""(function(){ var i = document.querySelector('#vault-detail .mp-search input'), ae = document.activeElement;
  return JSON.stringify({ focused: !!i && ae === i, same: i === window.__mpBox, value: i ? i.value : null,
    caret: i ? [i.selectionStart, i.selectionEnd] : null, activeTag: ae ? ae.tagName : null }); })()"""

_CACHE = {}


def _measure():
    """Render the window once per process at every width. -> dict, or raises with the reason."""
    if "r" in _CACHE:
        return _CACHE["r"]
    bible = os.path.join(ROOT, "bible.html")
    RC.require_chrome()   # REG-3061 - a browser that will not start is UNKNOWN for this law (a VenueFault), never a red
    res = {}
    try:
        t = RC._Tab("about:blank")
        t.send("Page.enable")
        t.send("Runtime.enable")
        t.send("Emulation.setDeviceMetricsOverride", width=WIDTHS[0][0], height=WIDTHS[0][1],
               deviceScaleFactor=1, mobile=False)
        try:
            t.send("Emulation.setFocusEmulationEnabled", enabled=True)
        except Exception:
            pass
        t.send("Page.navigate", url="file://" + bible)
        ready = False
        for _ in range(160):
            time.sleep(0.25)
            try:
                if t.ev("(function(){try{return !!(window.openMuleCard&&window.vaultAssign&&window.tvVaultRegister"
                        "&&window._mpLayout)}catch(e){return false}})()") is True:
                    ready = True
                    break
            except Exception:
                pass
        if not ready:
            raise AssertionError("bible.html never exposed openMuleCard in 40s — UNKNOWN, not passing")
        time.sleep(0.5)
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
        res["seeded"] = t.ev(SEED % (json.dumps(ITEMS), json.dumps(MULE)))
        for (w, h) in _W(WIDTHS):
            t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=(w < 500))
            time.sleep(0.25)
            # #174 R1 — what a mule opens on (the doll in front), then the stash in front
            _open(t, "equip")
            res["%dx%d" % (w, h)] = json.loads(t.ev(MEASURE))
            res["tight %dx%d" % (w, h)] = json.loads(t.ev(TIGHT))          # REG-1379 round 2
            _open(t, "stash")
            res["st %dx%d" % (w, h)] = json.loads(t.ev(MEASURE))
            res["tight st %dx%d" % (w, h)] = json.loads(t.ev(TIGHT))
            _open(t, "equip")
        # #174 v-B — the same widths with the doll in use and the picker open on the left hand
        t.send("Emulation.setDeviceMetricsOverride", width=WIDTHS[0][0], height=WIDTHS[0][1], deviceScaleFactor=1,
               mobile=False)
        time.sleep(0.25)
        res["equipped"] = _equip(t, MULE, WEAR)
        res["hover"] = {}
        for (w, h) in _W(HOVER_WIDTHS):
            t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=False)
            time.sleep(0.25)
            for view in ("stash", "equip"):
                res["hover"]["%dx%d %s-front" % (w, h, view)] = _hover_worn(t, view)
            _open(t, "equip")
        for (w, h) in _W(WIDTHS):
            t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=(w < 500))
            time.sleep(0.25)
            for view, key in (("stash", "eqs"), ("equip", "eq")):
                _open(t, view)
                t.ev("(function(){ window._mpPick('larm'); return 1; })()")
                time.sleep(0.35)
                res["%s %dx%d" % (key, w, h)] = json.loads(t.ev(MEASURE))
                res["tight %s %dx%d" % (key, w, h)] = json.loads(t.ev(TIGHT))
        t.ev("(function(){ window._mpPick(null); return 1; })()")
        # REG-1375 round 2 - the mule window's own tabs while its picker is open: Select (the left hand) and Edit (a database
        # helm placed through the host's Select), the doll and the stash in front, at every width; the helm comes off after
        res["helm"] = t.ev(HELM % json.dumps(MULE))
        time.sleep(0.3)
        # #42 - the helm goes on and comes off WHATEVER the restriction (the passes after it read the locker it leaves)
        for (w, h) in _W(WIDTHS):
            t.send("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=1, mobile=(w < 500))
            time.sleep(0.25)
            for view in ("equip", "stash"):
                for state, js in (("select", "window._mpPick('larm'); window._cbPickTab('select');"), ("edit", "window._mpPick('head');")):
                    _open(t, view)
                    t.ev("(function(){ %s return 1; })()" % js)
                    time.sleep(0.4)
                    res["mtabs %s %s %dx%d" % (state, view, w, h)] = json.loads(t.ev(MTABS))
                    t.ev("(function(){ window._mpPick(null); return 1; })()")
        res["unhelm"] = t.ev(UNHELM)
        time.sleep(0.2)
        # type in the Stats search, then re-render underneath him (v3889 #132: at 1280 - the phone keyboard step left)
        # ⚠ #42 - Lacerator is assigned WHATEVER the restriction: it stays in the locker through the reload below, so the
        # drag pass packs around it; skipping it would hand a restricted run a different stash from the full run's
        _typing = bool(_W(TYPE_AT))
        if _typing:
            t.send("Emulation.setDeviceMetricsOverride", width=TYPE_AT[0][0], height=TYPE_AT[0][1], deviceScaleFactor=1,
                   mobile=False)
            time.sleep(0.25)
            t.ev("(function(){ window.vaultCloseCard(); window.openMuleCard(%s); return 1; })()" % json.dumps(MULE))
            time.sleep(0.35)
            res["typing"] = t.ev(FOCUS_TYPE)
        t.ev("(function(){ window.vaultHandAdd('Lacerator'); window.vaultAssign('Lacerator', %s); return 1; })()"
             % json.dumps(MULE))
        time.sleep(0.3)
        if _typing:
            res["refresh"] = json.loads(t.ev(FOCUS_READ))
        if _W(DRAG_AT):
            try:
                res["drag"] = _drag_pass(t, bible)
            except Exception as e:          # the instrument failed: said once, as UNKNOWN, never as a pass
                res["drag"] = {"err": "the drag pass itself failed - UNKNOWN, not passing: %r" % (e,)}
        if _W(KEYS_AT):
            try:
                res["keys"] = _keys_pass(t)
            except Exception as e:
                res["keys"] = {"err": "the keyboard pass itself failed - UNKNOWN, not passing: %r" % (e,)}
        res["errors"] = list(getattr(t, "page_errors", []) or [])
        try:
            t.close()
        except Exception:
            pass
    finally:
        RC._chrome_down()
    _CACHE["r"] = res
    return res


def _near(a, b, tol):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


BAND_TOL = 1.5


def _states():
    """(label, measurement) for every width — #174 R1: the doll in front and the stash in front, each plain and with
    the doll in use + the picker open"""
    r = _measure()
    out = []
    for w, h in _W(WIDTHS):
        out.append(("%dx%d" % (w, h), r["%dx%d" % (w, h)]))
        out.append(("%dx%d stash-front" % (w, h), r["st %dx%d" % (w, h)]))
        out.append(("%dx%d equipped+picker" % (w, h), r["eq %dx%d" % (w, h)]))
        out.append(("%dx%d stash-front equipped+picker" % (w, h), r["eqs %dx%d" % (w, h)]))
    return out


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


class TheWindowFitsAtEveryWidth(unittest.TestCase):

    def test_the_fixture_reached_the_window(self):
        """PRINT THE DENOMINATOR: a window that rendered no text passes every check below."""
        r = _measure()
        self.assertEqual(r.get("seeded"), len(ITEMS), "the fixture did not put its items in the locker")
        # REG-1893 - a TV_LAW_WIDTHS restriction outside WIDTHS empties _states(); the denominator case then
        # measured no width and passed. Same door as every sibling: go on, or a DECLARED skip.
        _need(self, WIDTHS)
        for label, m in _states():
            self.assertNotIn("err", m, "%s: %s" % (label, m.get("err")))
            self.assertGreaterEqual(m["nText"], 120, "%s: only %d text nodes measured" % (label, m["nText"]))
        self.assertEqual(r.get("errors"), [], "the page threw while the window was open")

    def test_the_doll_in_use_was_really_measured(self):
        """#174 v-B — the equipped pass is only a check if the doll WAS in use: three items worn through the picker,
        stat values drawn, the picker open with choices in it — at every width."""
        r = _measure()
        self.assertEqual(r.get("equipped"), [p[1] for p in WEAR], "the picker did not equip the fixture's items")
        _need(self, WIDTHS)   # REG-1893 - "at every width" over no width is a pass that measured nothing
        for w, h in _W(WIDTHS):
            m = r["eq %dx%d" % (w, h)]
            self.assertEqual((m["worn"], m["pick"]), (len(WEAR), 1), "%dx%d: worn %s, picker %s" % (w, h, m["worn"], m["pick"]))
            self.assertGreater(m["sv"], 0, "%dx%d: no stat value was drawn from the worn gear" % (w, h))
            self.assertGreater(m["opts"], 0, "%dx%d: the left-hand picker offered nothing" % (w, h))

    def test_no_word_or_control_is_cut_or_outside_its_panel(self):
        _need(self, WIDTHS)
        bad = []
        for label, m in _states():
            bad += ["%s %s" % (label, x) for x in m["cut"] + m["outside"]]
        self.assertEqual(bad, [], "text or a control in the mule window is cut or spills out of its panel:\n  "
                         + "\n  ".join(bad))

    def test_nothing_scrolls_sideways(self):
        _need(self, WIDTHS)
        bad = []
        for label, m in _states():
            if m["hscroll"][0] > m["hscroll"][1] + 1:
                bad.append("%s the window itself %d/%d" % (label, m["hscroll"][0], m["hscroll"][1]))
            bad += ["%s %s" % (label, x) for x in m["sideways"]]
        self.assertEqual(bad, [], "part of the mule window scrolls sideways:\n  " + "\n  ".join(bad))

    def test_the_gold_box_is_one_line_and_the_stash_never_scrolls(self):
        """#174 v-B review — the stash cell budget assumes a one-line gold box; a second line scrolled the stash view
        and cut the box's border at 2000 wide. In columns, plain and with the doll in use, at every width."""
        _need(self, WIDTHS)
        bad, seen = [], 0
        for label, m in _states():
            if m.get("stack") or m.get("goldLines") is None:
                continue
            seen += 1
            if round(m["goldLines"]) != 1:
                bad.append("%s the gold box is %.2f lines: %r" % (label, m["goldLines"], m["goldText"]))
            if m["stashScroll"] and m["stashScroll"][0] > m["stashScroll"][1]:
                bad.append("%s the stash view scrolls %d/%d" % (label, m["stashScroll"][0], m["stashScroll"][1]))
        self.assertGreaterEqual(seen, _floor(10, WIDTHS), "the gold box was measured at only %d column-layout states" % seen)
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_no_header_title_runs_under_its_control(self):
        _need(self, WIDTHS)
        bad = []
        for label, m in _states():
            bad += ["%s %s" % (label, x) for x in m["collide"]]
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_the_type_is_its_token_times_the_unit_never_below_the_floor(self):
        _need(self, WIDTHS)
        r = _measure()
        for w, h in _W(WIDTHS):
            m = r["%dx%d" % (w, h)]
            # the LAW, not the numbers: the root tokens are read off the page, so a retuned scale still grades
            tok = m["tokens"]
            for key in ("title", "meta", "micro"):
                self.assertTrue(tok.get(key) and tok[key] > 0, "%dx%d: the root --fs-%s token could not be read "
                                                                "off the page — UNKNOWN, not passing" % (w, h, key))
            kf = min(1.0, m["k"])
            for key in ("title", "meta"):
                self.assertIsNotNone(m["fs"][key], "%dx%d: no %s text to read a size from (.mp-h-t / .mp-left "
                                                   ".mp-empty) — the markup this law reads has moved" % (w, h, key))
                want = max(tok["micro"], tok[key] * kf)
                self.assertAlmostEqual(m["fs"][key], want, delta=0.05,
                                       msg="%dx%d (k=%.4f): the %s type is %.2fpx, not max(--fs-micro %g, --fs-%s %g "
                                           "x %.4f) = %.2fpx" % (w, h, m["k"], key, m["fs"][key], tok["micro"], key,
                                                                tok[key], kf, want))

    def test_at_2000_the_panels_and_the_doll_are_their_measured_rects(self):
        """their rects, with the one declared upgrade (_ours / _our_slot) — plain and with the doll in use"""
        _need(self, ((2000, 1300),))
        bad = []
        for key in ("st 2000x1300", "eqs 2000x1300"):      # #174 R1 — their arrangement is the stash in front
            m = _measure()[key]
            self.assertEqual(m["k"], 1.0)
            for c in THEIR_PANELS:
                want, got = _ours(c), m["panels"][c]
                # REG-1379 round 2: heights included again - no panel is stretched into the glass under it
                if not got or not _near(got, want, SW_TOL if c == "mp-sw" else TOL_2000):
                    bad.append("%s %s %s, measured %s" % (key, c, [round(v, 2) for v in want],
                                                          [round(x, 2) for x in got] if got else None))
            for s in THEIR_SLOTS:
                want, got = _our_slot(s), m["slots"].get(s)
                if not got or not _near(got, want, 0.5):
                    bad.append("%s slot %s %s, measured %s" % (key, s, list(want), got))
        self.assertEqual(bad, [], "at 2000x1300 the window left their geometry:\n  " + "\n  ".join(bad))

    def test_with_the_doll_in_front_it_is_big_in_the_centre_and_the_stash_takes_its_rect(self):
        """#174 R1 — his order: the character front and centre, the stash smaller at the side. At 2000 the doll + inventory
        panel is their 322x364 body on MP_EQ_BIG, centred in the centre panel under its tab band; the side stash takes
        EQUIPMENT's own rect at the left (their 322x400); every slot is their rect on the big unit. Plain and in use."""
        import re as _re
        _need(self, ((2000, 1300),))
        with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as f:
            big = float(_re.search(r"var MP_EQ_BIG = ([0-9.]+),", f.read()).group(1))
        bad = []
        for key in ("2000x1300", "eq 2000x1300"):
            m = _measure()[key]
            self.assertEqual(m["front"], "equip", "%s: the mule did not open with EQUIPMENT in front" % key)
            ss, eq, cp = m["panels"]["mp-sstash"], m["panels"]["mp-eq"], m["panels"]["mp-cp"]
            if not ss or not _near(ss, _ours("mp-eq"), TOL_2000):
                bad.append("%s side stash %s, measured %s" % (key, list(_ours("mp-eq")), ss))
            want = [cp[0] + (cp[2] - 322 * big) / 2, cp[1] + 36 + 8, 322 * big, 364 * big]
            if not eq or not _near(eq, want, 1.0):
                bad.append("%s big doll panel %s, measured %s" % (key, [round(v, 1) for v in want], eq))
            for s in THEIR_SLOTS:
                x, y, w, h = THEIR_SLOTS[s]
                want_s, got = (x * big, (y - THEIR_EQ[0]) * big, w * big, h * big), m["slots"].get(s)
                if not got or not _near(got, want_s, 0.75):
                    bad.append("%s slot %s %s, measured %s" % (key, s, [round(v, 1) for v in want_s], got))
        self.assertEqual(bad, [], "with the doll in front the window is not the big doll + the side stash:\n  " + "\n  ".join(bad))

    def test_at_1280_the_fixed_panels_are_their_rects_times_the_unit(self):
        _need(self, ((1280, 800),))
        m = _measure()["st 1280x800"]
        k = m["k"]
        self.assertLess(k, 1.0)
        bad = []
        for c in ("mp-eq", "mp-cp", "mp-notes", "mp-stats", "mp-set"):
            want = [v * k for v in _ours(c)]
            if c == "mp-stats":
                # #174 v-B2 — STATS ends at the window's bottom (its list scrolls inside): min(726k, the room below it)
                # #76 v3755 — the Summary (mp-show) now lists Items AND physical Copies; that 5th row grows it past its
                # 150u floor to fit its content (measured 139.4 vs the 136.9 floor at 1280, kv not scrolling), nudging
                # STATS ~2.5px down. Pin STATS flush below the Summary's REAL bottom + the 6u gap, not the floored 312u;
                # its max-height stays the CSS 100vh-30-312u, so it ends ~2.5px lower but well inside the glass. The
                # Summary itself is pinned just below (spec top/left, at-least its floor). Law, not a number.
                sh = m["panels"]["mp-show"]
                want[1] = sh[1] + sh[3] + 6 * k
                want[3] = min(726 * k, m["vh"] - 30 - 312 * k)
            if not _near(m["panels"][c], want, 1.0):
                bad.append("%s %s, measured %s" % (c, [round(v, 1) for v in want], [round(v, 1) for v in m["panels"][c]]))
        # #76 v3755 — the Summary (mp-show) sits at its spec top/left and never shrinks below its 150u floor; it is
        # allowed to GROW to fit the Items + physical Copies rows (that growth is what moves STATS down, pinned above).
        sh, ws = m["panels"]["mp-show"], _ours("mp-show")
        if (not sh or abs(sh[0] - ws[0] * k) > 1.0 or abs(sh[1] - ws[1] * k) > 1.0
                or abs(sh[2] - ws[2] * k) > 1.0 or sh[3] < ws[3] * k - 1.0):
            bad.append("mp-show [%s, %s, %s, >=%s], measured %s"
                       % (round(ws[0] * k, 1), round(ws[1] * k, 1), round(ws[2] * k, 1), round(ws[3] * k, 1),
                          [round(v, 1) for v in sh] if sh else None))
        # #174 R1 — with the doll in front the side stash is EQUIPMENT's rect times the unit (their 400 kept at 1280)
        m2 = _measure()["1280x800"]
        want = [v * k for v in _ours("mp-eq")]
        if not m2["panels"]["mp-sstash"] or not _near(m2["panels"]["mp-sstash"], want, 1.0):
            bad.append("side stash %s, measured %s" % ([round(v, 1) for v in want], m2["panels"]["mp-sstash"]))
        self.assertEqual(bad, [], "at 1280 the window is not their geometry times k:\n  " + "\n  ".join(bad))

    def test_in_his_console_at_1280_the_part_he_packs_from_fits_the_window(self):
        """#174 v-B2 — the Grok seat's "bottoms sliced" at 1280, reproduced at 1280x695 (the console's board): the stash
        panel ran 64px and PRIMARY SKILLS 37px under the glass. Header, mule bar, doll + inventory and the stash panel
        (its page bar and gold box inside it) now end inside the window, and STATS ends at its bottom."""
        _need(self, (CONSOLE,))
        bad = []
        # #42 - the unit is compared with 1280x800's wherever that viewport was measured too (always, unrestricted)
        k800 = _measure()["1280x800"]["k"] if LW.at((1280, 800), _ONLY) else None
        for key in ("%dx%d" % CONSOLE, "eq %dx%d" % CONSOLE, "st %dx%d" % CONSOLE, "eqs %dx%d" % CONSOLE):
            m = _measure()[key]
            if k800 is not None:
                self.assertLess(m["k"], k800, "%s: the height did not set the unit" % key)
            for c in ("mp-set", "mp-eq", "mp-sstash", "mp-cp", "mp-prim", "mp-stats"):
                if not m["panels"].get(c):
                    # the #231 eye on v3507: a missing panel was SKIPPED, so a doll or a stats panel that vanished
                    # passed. Only the side stash may be absent, and only with the stash in front.
                    if c == "mp-sstash" and key.startswith(("st ", "eqs ")):
                        continue
                    bad.append("%s %s is not on the page at all" % (key, c))
                    continue
                bottom = m["mpTop"] + m["panels"][c][1] + m["panels"][c][3]
                if bottom > m["vh"] + 0.5:
                    bad.append("%s %s ends %.1fpx under the window's bottom" % (key, c, bottom - m["vh"]))
        self.assertEqual(bad, [], "\n  ".join(bad))

    def test_the_hover_card_never_covers_the_mule_bar(self):
        """#174 v-B2 — hovered with a real mouse move, the card of a worn weapon stays under the EQUIPMENT header: on
        v-B it rose over MULES IN THIS LOCKER and read it "ES IN THIS LOCKER". #174 v-B2 integration: the card is the
        builder's in-game box (#cb-tip) naming the hovered item, the board's #arttip stays shut; the worn ring (a short
        box that fits above it) and a stash tile are hovered too, and no box rises over its own panel's header."""
        _need(self, HOVER_WIDTHS)
        hover = _measure()["hover"]
        self.assertEqual(len(hover), 2 * len(_W(HOVER_WIDTHS)), "the hover card was measured at %d size x arrangement pairs, not %d"
                         % (len(hover), 2 * len(_W(HOVER_WIDTHS))))
        seen = 0
        for size, byItem in sorted(hover.items()):
            self.assertEqual(sorted(byItem), ["ring", "stash", "weapon"], "%s: hovered %s" % (size, sorted(byItem)))
            for what, hv in sorted(byItem.items()):
                key = "%s %s" % (size, what)
                self.assertNotIn("err", hv, "%s: %s" % (key, hv.get("err")))
                self.assertTrue(hv["on"], "%s: the in-game box never showed - UNKNOWN, not passing" % key)
                self.assertEqual(hv["name"], hv["want"], "%s: the box names %r, the hovered item is %r" % (key, hv["name"], hv["want"]))
                self.assertFalse(hv["arttip"], "%s: the board's #arttip opened too - two boxes for one hover" % key)
                self.assertFalse(hv["overBar"], "%s: the box %s covers the mule bar %s" % (key, hv["tip"], hv["bar"]))
                self.assertGreaterEqual(hv["tip"][1], hv["headBottom"] - 0.5, "%s: the box rose over its panel's header" % key)
                seen += 1
        self.assertEqual(seen, 6 * len(_W(HOVER_WIDTHS)), "PRINT THE DENOMINATOR: %d of %d hovers were measured" % (seen, 6 * len(_W(HOVER_WIDTHS))))

    def test_a_real_drag_locks_an_item_where_it_is_dropped_and_a_reload_keeps_it(self):
        _need(self, DRAG_AT + KEYS_AT)
        dr = _measure()["drag"]
        self.assertNotIn("err", dr, dr.get("err"))
        for key in ("2000", "console"):
            d = dr[key]
            self.assertTrue(d["from"] and d["from"]["hit"], "%s: the ring could not be pressed (covered or absent): %s" % (key, d["from"]))
            self.assertEqual(d.get("mid"), {"drop": "vd-drop vd-drop-ok", "ghost": True},
                             "%s: in the air the ring showed no ghost or no green footprint: %s" % (key, d.get("mid")))
            want = d["want"]
            for when in ("after", "reloaded"):
                t = d[when]
                self.assertTrue(t, "%s %s: the ring is not in the window" % (key, when))
                self.assertEqual((t["area"], t["x"], t["y"], t["held"]), (want[0], want[1], want[2], True),
                                 "%s %s: the ring is not locked on the cell it was dropped on: %s" % (key, when, t))
                # the lock is a corner badge: a press on the ring's centre must pick the ring up, never unlock it
                self.assertFalse(t["lock"], "%s %s: the ring's centre is its unlock button - the next press there "
                                            "would unlock it instead of moving it" % (key, when))
            self.assertEqual(dict((k, d["store"].get(k)) for k in ("tab", "x", "y", "page")),
                             {"tab": want[0], "x": want[1], "y": want[2], "page": 0}, "%s: the store does not hold the drop" % key)

    def test_a_drop_that_does_not_fit_is_refused_on_screen(self):
        _need(self, DRAG_AT + KEYS_AT)
        self.assertNotIn("err", _measure()["drag"], _measure()["drag"].get("err"))
        d = _measure()["drag"]["refuse"]
        self.assertTrue(d["from"] and d["from"]["hit"], d["from"])
        self.assertEqual(d.get("mid"), {"drop": "vd-drop vd-drop-no", "ghost": True}, "a 2x4 past the edge was not tinted red in the air")
        self.assertEqual((d["after"]["x"], d["after"]["y"], d["after"]["held"]), (d["from"]["x"], d["from"]["y"], False),
                         "a refused 2x4 moved or was locked")
        self.assertNotIn(d["from"]["key"], d["store"], "a refused drop wrote the store")
        self.assertIs((d["said"] or {}).get("ok"), False)
        self.assertIn("stays where it was", (d["said"] or {}).get("t", ""))

    def test_the_keyboard_carries_an_item_right_click_unlocks_it_and_a_stash_tab_takes_a_drop(self):
        _need(self, DRAG_AT + KEYS_AT)
        d = _measure()["drag"]
        self.assertNotIn("err", d, d.get("err"))
        k = d["keys"]
        self.assertTrue(k["focused"], "the ring could not take focus")
        self.assertEqual(k["carry"], "vd-drop vd-drop-ok", "Enter did not pick the ring up (no footprint shown)")
        self.assertEqual((k["after"]["x"], k["after"]["y"], k["after"]["held"]), (8, 8, True),
                         "Enter, Left, Up, Enter did not move the ring one cell up-left and lock it: %s" % k["after"])
        self.assertIs(k["open"], True, "a carried item's keys closed the window")
        r = d["unlock"]
        self.assertFalse(r["after"]["held"], "a right-click did not unlock the ring")
        self.assertNotIn(r["after"]["key"], r["store"], "the unlock left his spot in the store")
        g = d["gems"]
        self.assertTrue(g["from"] and g["from"]["hit"], g["from"])
        self.assertIs(g.get("over"), True, "the Gems tab did not light up under the dragged item")
        self.assertEqual((g["after"]["area"], g["after"]["x"], g["after"]["y"], g["after"]["held"]), ("gems", 0, 0, True),
                         "a drop on the Gems tab did not land in the Gems tab's first cell: %s" % g["after"])

    # v3889 (#132) - test_at_375_a_drag_scrolls_the_window_to_another_mules_tab left with the phone page (its tombstone
    # is in test_there_is_no_phone_page); the desktop drag to another mule is test_a_real_drag_locks_... above

    def test_the_keyboard_carries_an_item_to_another_mule(self):
        _need(self, KEYS_AT)
        ks = _measure()["keys"]
        self.assertNotIn("err", ks, ks.get("err"))
        kb = ks["keys"]
        self.assertTrue(kb["focused"], "the stash item could not take focus")
        self.assertIs(kb["over"], True, "] did not point the carried item at the next mule's tab")
        self.assertIn("Mule 2", (kb["said"] or {}).get("t", ""))
        self.assertEqual(kb["page"], 1, "Enter after ] did not move the item to Mule 2")

    # v3889 (#132) - test_a_finger_can_unlock_a_placed_item (a touch tap at 375) and
    # test_a_keyboard_opening_leaves_the_search_box_he_is_typing_in (a phone keyboard, a height-only resize) left with
    # the phone page; their tombstones are in test_there_is_no_phone_page

    def test_a_re_render_underneath_him_puts_the_caret_back(self):
        _need(self, TYPE_AT)
        rf = _measure()["refresh"]
        self.assertTrue(rf["focused"], "an item assigned in the background re-rendered the window and left the "
                                       "focus on %s, not the search box he was typing in" % rf["activeTag"])
        self.assertEqual((rf["value"], rf["caret"]), ("fire", [2, 3]), rf)

    def _tights(self):
        r = _measure()
        return [(k[len("tight "):], v) for k, v in sorted(r.items()) if k.startswith("tight ")]

    def test_r2_the_window_is_as_tall_as_what_it_holds(self):
        """REG-1379 his "Tighten both" (round 2): in every arrangement at every width, where the window does not scroll it
        ends under its content by its own bottom padding and above the glass's bottom - no band (at 2000x1300 it ran 248px
        past their rects to the glass); where it scrolls it is the glass's height exactly, scrolling inside itself"""
        _need(self, WIDTHS)
        bad, fits, scrolls = [], 0, 0
        tights = self._tights()
        self.assertGreaterEqual(len(tights), 4 * len(_W(WIDTHS)), "PRINT THE DENOMINATOR: %d window states measured" % len(tights))
        for label, m in tights:
            self.assertNotIn("err", m, "%s: %s" % (label, m.get("err")))
            if m["sh"] <= m["ch"] + 1:
                fits += 1
                band = m["win"][1] - m["mp"][1] - m["padB"]
                if band > BAND_TOL:
                    bad.append("%s: %.0fpx of empty band under the content, inside the window (it ends at %.0f of the glass's %.0f)"
                               % (label, band, m["win"][1], m["vh"]))
            else:
                scrolls += 1
                if abs((m["win"][1] - m["win"][0]) - m["vh"]) > 0.5:
                    bad.append("%s: it scrolls inside itself but is %.0fpx tall on a %.0fpx glass" % (label, m["win"][1] - m["win"][0], m["vh"]))
        # #42 - each premise names the viewport that carries it, so it binds wherever that viewport is measured
        self.assertGreaterEqual(fits, 4 if LW.at((2000, 1300), _ONLY) else 0, "PREMISE: only %d states fit the glass - 2000x1300 alone is four" % fits)
        # v3889 (#132) - the scrolling half's premise was 375x812; measured 11-09 at his console's 1280x695 (and 1120x628,
        # 800x1000) all four states scroll, so it binds there now
        self.assertGreaterEqual(scrolls, 4 if LW.at(CONSOLE, _ONLY) else 0, "PREMISE: only %d states scroll - his console's 1280x695 alone is four" % scrolls)
        self.assertEqual(bad, [], "the mule window is not as tall as what it holds:\n  " + "\n  ".join(bad))

    def test_r2_no_panel_is_stretched_past_what_it_holds(self):
        """REG-1379 (round 2, reproduced on fe817ab7): round 1 filled the band by stretching the last panels - at 2000x1300
        STRENGTHS AND WEAKNESSES was ~330px of empty bordered box and NOTES ~370px of empty textarea. In columns, every
        arrangement at every width: STRENGTHS AND WEAKNESSES is no taller than its own content (or its 57u floor), measured
        with every stretch taken away; NOTES is its 206u; STATS its 726u at most"""
        _need(self, WIDTHS)
        bad, seen = [], 0
        for label, m in self._tights():
            if m.get("err") or m.get("stack"):
                continue
            seen += 1
            k = m["k"]
            if m["sw"] is None or m["swNat"] is None:
                bad.append("%s: STRENGTHS AND WEAKNESSES is not drawn" % label)
            elif m["sw"] > m["swNat"] + BAND_TOL:
                bad.append("%s: STRENGTHS AND WEAKNESSES is %.0fpx tall and holds %.0fpx - %.0fpx of empty box"
                           % (label, m["sw"], m["swNat"], m["sw"] - m["swNat"]))
            if m["notes"] is None or m["notes"] > 206 * k + BAND_TOL:
                bad.append("%s: NOTES is %spx, not its 206u (%.0f)" % (label, m["notes"], 206 * k))
            if m["stats"] is None or m["stats"] > 726 * k + BAND_TOL:
                bad.append("%s: STATS is %spx, past its 726u (%.0f)" % (label, m["stats"], 726 * k))
        # four arrangements at each column width (six of the eight; #42: of those this run measures)
        self.assertGreaterEqual(seen, 4 * len([x for x in _W(WIDTHS) if x[0] > 900]), "PREMISE: only %d column states were measured" % seen)
        self.assertEqual(bad, [], "a mule window panel is stretched past what it holds:\n  " + "\n  ".join(bad))

    def test_r2_the_mule_windows_tabs_stay_in_view_while_its_picker_is_open(self):
        """REG-1375 (round 2, reproduced on fe817ab7): the #174 Edit panel lives in the mule window, and the builder's tab
        rule skipped the mule host - the Select and Edit modals covered EQUIPMENT / STASH at every width, the phone sheet all
        four. At every width, the doll and the stash in front, Select and Edit: where the mule's tab row is on the glass with
        room under it, the modal does not overlap it and each tab's centre hit-tests to that tab"""
        _need(self, WIDTHS)
        r, bad, seen = _measure(), [], 0
        self.assertTrue(str(r.get("helm") or "").startswith("u"), "PREMISE: no database helm was placed, so Edit could not open: %r" % r.get("helm"))
        for key, tb in sorted(r.items()):
            if not key.startswith("mtabs "):
                continue
            if not tb.get("modal"):
                bad.append("%s: PREMISE - no modal was open" % key)
                continue
            if "err" in tb:
                bad.append("%s: %s" % (key, tb["err"]))
                continue
            if key.startswith("mtabs edit") and not tb.get("edit"):
                bad.append("%s: PREMISE - the helm opened on %r, not its Edit tab" % (key, tb.get("tab")))
            if key.startswith("mtabs select") and tb.get("tab") != "Select":
                bad.append("%s: PREMISE - the left hand opened on %r, not Select" % (key, tb.get("tab")))
            if not tb["onScreen"] or tb["room"] < 280:
                continue          # the row is off the glass (or has no room under it): nothing to keep in view here
            seen += 1
            if tb["over"]:
                bad.append("%s: the modal %s lies over the mule's tab row %s" % (key, [round(v) for v in tb["at"]], [round(v) for v in tb["tabs"]]))
            hidden = [x["tab"] for x in tb["hit"] if not x["seen"]]
            if hidden or len(tb["hit"]) != 4:
                bad.append("%s: tabs not in view: %s (of %d)" % (key, hidden, len(tb["hit"])))
        self.assertGreaterEqual(seen, 4 * len(_W(WIDTHS)), "PREMISE: the mule's tab row was checked in only %d modal states" % seen)
        self.assertEqual(r.get("unhelm"), 1, "the fixture's helm did not come off after the tabs pass")
        self.assertEqual(bad, [], "a modal hides the mule window's tabs:\n  " + "\n  ".join(bad))


RED_PROOF = [
    {
        "why": "REG-1379 round 2 - the mule window is the glass's height again: 248px of empty band under their rects at 2000x1300",
        "file": "bible.html",
        "find": ".vault-detail.vd-fs.mp-on{bottom:auto;max-height:100vh;max-height:100dvh;",
        "replace": ".vault-detail.vd-fs.mp-on{",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "REG-1379 round 2 - round 1's fix again: the last panels stretch into the band (S&W an empty box, NOTES an empty textarea)",
        "file": "bible.html",
        "find": ".vault-detail.vd-fs.mp-on{bottom:auto;max-height:100vh;max-height:100dvh;",
        "replace": ".mp:not(.mp-stack){min-height:calc(100vh - 44px);align-items:stretch}\n.mp:not(.mp-stack) > .mp-main{display:flex;flex-direction:column}\n"
                   ".mp:not(.mp-stack) .mp-lc{flex:1 1 auto;align-items:stretch}\n.mp:not(.mp-stack) .mp-left > :last-child,.mp:not(.mp-stack) .mp-centre > "
                   ":last-child,.mp:not(.mp-stack) .mp-right > .mp-stats{flex-grow:1}\n.vault-detail.vd-fs.mp-on{",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "REG-1375 round 2 - the mule host's modal is placed with no tab rule again: it covers the mule's EQUIPMENT / STASH tabs",
        "file": "bible.html",
        "find": "    var _tr = _cbTabsBottom(vh, mh0);\n",
        "replace": "    var _tr = mh0 ? null : _cbTabsBottom(vh, mh0);\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B2 fix round - the window stops scrolling under a drag (at 375 another mule's tab is out of reach)",
        "file": "bible.html",
        "find": "    _mpTrack(d, e.clientX, e.clientY);\n    _mpAutoScroll(d, e.clientX, e.clientY);\n",
        "replace": "    _mpTrack(d, e.clientX, e.clientY);\n",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B2 fix round - the keyboard carry has no key that changes mule again",
        "file": "bible.html",
        "find": "      if (k === '[' || k === ']'){\n",
        "replace": "      if (false){\n",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B2 fix round - the lock is a 10px target on a phone again",
        "file": "bible.html",
        "find": "  .mp .vd-unlock::after{content:\"\";position:absolute;inset:-10px}\n",
        "replace": "",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        # #174 v-B moved the tightest prose panel: the LEFT column is now their 322 on the doll's unit, so MERCENARY's
        # sentence fits its 80u at every width (scanned 320..1600 with the panel fixed: never cut), while STRENGTHS
        # AND WEAKNESSES, fixed at its 57u, cuts its sentence at 1024, 960, 920 and 901 wide. The defect class is the
        # same — a prose panel with a fixed height cuts its own sentence — so the proof now aims where it still bites.
        "why": "#174 - a prose panel (STRENGTHS AND WEAKNESSES) is a fixed height again, so its sentence is cut where the words out-grow it",
        "file": "bible.html",
        "find": ".mp-sw{min-height:calc(57*var(--u))}\n",
        "replace": ".mp-sw{height:calc(57*var(--u))}\n",
        "matches": 1,
        # #42 measured 2026-09-29: green alone at 1280x800 / 2000x1300 / 375x812 / 1280x695 / 390x844; the full sweep
        # cuts it at 1024x768 and 901x900
        "widths": ["1024x768"],
    },
    {
        "why": "#174 v-B - the picker's choice never reaches the doll, so the equipped pass measures an empty doll and calls it fitting",
        "file": "bible.html",
        "find": "      try { _mpEqWrite(r.all); }\n",
        "replace": "      try { void 0; }\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B review - the gold box says its worn copies in a sentence that wraps it, and the stash view scrolls",
        "file": "bible.html",
        "find": "+ ' in inventory · ' + _wornHere + ' worn</div>'",
        "replace": "+ ' in inventory · ' + _wornHere + ' worn on the doll · ' + (_thisMuleN + _wornHere) + ' on this mule</div>'",
        "matches": 1,
        # #42 measured 2026-09-29: green alone at 1280x800 / 2000x1300 / 375x812 / 1280x695 / 390x844; the full sweep
        # wraps it at 1120x628, 1024x768 and 901x900
        "widths": ["1024x768"],
    },
    {
        "why": "#174 v-B review - a doll slot stops taking the pointer, so real input cannot open it (a .click() would have)",
        "file": "bible.html",
        "find": ".mp-slot.mp-gone{border-color:var(--hell);border-style:dashed}\n",
        "replace": ".mp-slot.mp-gone{border-color:var(--hell);border-style:dashed}\n.mp-slot{pointer-events:none}\n",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 v-B2 - the hover card of an item rises over its panel's header again (it read ES IN THIS LOCKER); since the integration the card is window.d2Tip and its floor is passed here",
        "file": "bible.html",
        "find": "    window.d2Tip.show(entry, el, { floor: floorOf(el) });\n",
        "replace": "    window.d2Tip.show(entry, el);\n",
        "matches": 1,
        "widths": ["1280x695"],   # #42 measured 2026-09-29: the tampered law is red at 1280x695 alone
    },
    {
        "why": "#174 v-B2 integration - the board's #arttip opens over the mule window's in-game box again: two boxes for one hover",
        "file": "bible.html",
        "find": "      try { if (window.D2TIP_OWNS && window.D2TIP_OWNS(e.target)) return; } catch (_e) {}\n",
        "replace": "",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B2 integration - the mule window's hover opens no in-game box at all (the lane listens to nothing)",
        "file": "bible.html",
        "find": "    if (el !== cur) show(el);\n",
        "replace": "",
        "matches": 1,
        # #42 measured 2026-09-29: red at 1280x695 alone (the hover card); the first probe's red at 1280x800 was
        # test_at_1280_the_fixed_panels' 6px font-reflow flake, not this defect - the push-time run caught it BLIND
        "widths": ["1280x695"],
    },
    {
        "why": "#174 v-B2 - the unit answers the width alone again, so in his console at 1280 the stash he packs from runs under the glass",
        "file": "bible.html",
        "find": "return { stack: false, k: Math.min(grow, (vw - 48) / MP_COL_W, Math.max(MP_K_FLOOR, (vh - MP_PAD_V) / MP_WORK_H)) };",
        "replace": "return { stack: false, k: Math.min(grow, (vw - 48) / MP_COL_W) };",
        "matches": 1,
        "widths": ["1280x695"],   # #42 measured 2026-09-29: the tampered law is red at 1280x695 alone
    },
    {
        "why": "#174 v-B2 - a dragged item lands one cell off from where it was let go (the drop reads the wrong cell)",
        "file": "bible.html",
        "find": "    return { x: Math.floor((cx - r.left - g.clientLeft - 3) / p), y: Math.floor((cy - r.top - g.clientTop - 3) / p) };\n",
        "replace": "    return { x: Math.floor((cx - r.left - g.clientLeft - 3) / p) - 1, y: Math.floor((cy - r.top - g.clientTop - 3) / p) };\n",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B2 - a drag never starts: the tiles take no pointer (his_mule_locked_21 - the ring would not move)",
        "file": "bible.html",
        "find": "    var it = e.target.closest('#vault-detail .vd-item[data-key], #vault-detail .vd-item[data-dbkey]'), g = it && it.closest('.vd-grid[data-area]');\n",
        "replace": "    var it = null, g = null;\n",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B2 - the keyboard cannot pick an item up",
        "file": "bible.html",
        "find": "      _mpCarry = { key: it.getAttribute('data-key'), el: it, grid: g, w: +it.getAttribute('data-w') || 1, h: +it.getAttribute('data-h') || 1,\n",
        "replace": "      return; _mpCarry = { key: it.getAttribute('data-key'), el: it, grid: g, w: +it.getAttribute('data-w') || 1, h: +it.getAttribute('data-h') || 1,\n",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 v-B2 - STATS runs under the glass again at 1280 (the Grok seat: Stats stops at Life)",
        "file": "bible.html",
        "find": ".mp:not(.mp-stack) .mp-stats{max-height:calc(100vh - 30px - 312*var(--u))}\n",
        "replace": "",
        "matches": 1,
        # #42 re-measured 2026-09-29, this proof alone, one Chrome: at 1280x800 the clean run is green (15.2 s) and the
        # tampered run red (13.8 s) in test_at_1280_the_fixed_panels_are_their_rects_times_the_unit on the defect
        # itself - mp-stats 485.3 px tall -> 662.5 px, STATS running under the glass - not the 6 px reflow flake that
        # misled proof 13's probe. (The first push-time run stopped at 13 and never reached this proof.) It is also red
        # at 1280x695 alone, the declaration it carried before.
        "widths": ["1280x800"],
    },
    {
        "why": "#174 v-B2 - the lock badge covers a small tile's centre again (1280 inventory), so pressing the ring unlocks it",
        "file": "bible.html",
        "find": "height:calc(12*var(--u));max-width:40%;max-height:40%;overflow:hidden;display:flex;",
        "replace": "height:calc(12*var(--u));min-width:12px;min-height:12px;overflow:hidden;display:flex;",
        "matches": 1,
        "widths": ["2000x1300"],   # #42 measured 2026-09-29: the tampered law is red at 2000x1300 alone
    },
    {
        "why": "#174 - openMuleCard stops writing --kf, so the window's type no longer rides its unit",
        "file": "bible.html",
        "find": "style=\"--u:'+k.toFixed(4)+'px;--kf:'+Math.min(1, k).toFixed(4)+'\"",
        "replace": "style=\"--u:'+k.toFixed(4)+'px\"",
        "matches": 1,
        "widths": ["1280x800"],   # #42 measured 2026-09-29: the tampered law is red at 1280x800 alone
    },
    {
        "why": "#174 - a background re-render no longer puts the caret back in the Stats search box",
        "file": "bible.html",
        "find": "      if (_in){ try { _in.focus({ preventScroll: true }); _in.setSelectionRange(_keep.q[0], _keep.q[1]); } catch (e) {} }\n",
        "replace": "",
        "matches": 1,
        # v3889 (#132): the typing pass left the phone's 390x844 for 1280x800 (TYPE_AT), so the proof measures there
        "widths": ["1280x800"],
    },
]
# v3889 (#132, his 11-08 "i dont need any mobile anything") - four red-proofs left with the phone page, each red at a phone
# width alone (measured 2026-09-29) and so blind at every width this law still renders: the mule host's phone sheet over
# the tabs (375), the stash gold box and the mule tab row wrapping (375), and a phone keyboard's height-only resize (390;
# its case left too - tombstones in test_there_is_no_phone_page)


if __name__ == "__main__":
    # A class-level skip would print OK (skipped=N) and exit 0, which run_gates reads as a PASS. With no browser
    # binary at all this is a DECLARED skip (77) that the gate's skip_ok names; everything else runs and can fail.
    if _ONLY is not None:
        sys.stderr.write("⚠ " + LW.banner(_ONLY, VIEWPORTS) + "\n")
    if not os.path.exists(RC.CHROME):
        sys.stderr.write("⚪ SKIP — %s. UNMEASURED, declared as a skip (77), never a pass.\n" % NO_BROWSER)
        raise SystemExit(77)
    unittest.main(verbosity=2)
