# -*- coding: utf-8 -*-
"""REG-3071 (#36, GrokBot 04:03) - A SOCKET RANGE NEVER PASSES ITS BASE.

The builder's tooltip said Aldur's Rhythm "Socketed (2-5)" - its own data line (s68: sock 2-5) - while a Jagged Star
holds at most 3, and the game caps an item's sockets at its base's ceiling. A display rule, never a data edit: every
surface that prints an item's lines asks one door (_cbSockCapLine), which caps a numeric socket range at
_cbMaxSock(base, item level) and passes any other line, and a base the database cannot read, unchanged. The surfaces:
the tooltip (_cbTipEntry), the socket stepper's range (_cbSockRange), a fixed count (_cbEntryFor), the Edit tab's lines
and its picked mods, and a d2jsp post's lines. Swept over the whole database on the page in node: three items printed past
their base (Aldur's Rhythm 2-5 on a Jagged Star, Heaven's Light 1-3 on a Mighty Scepter, Blade of Ali Baba 3 on a Tulwar),
and a magic Jeweler's (Socketed 4) on a Jagged Star printed 4. RED_PROOF below.
"""
import json
import os
import re
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
import vault_page_node as VPN  # noqa: E402

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")

BODY = r"""
(function(){
var W = window, d = W._cbDb();
function code(name){ return Object.keys(d.b).filter(function(k){ return d.b[k][0] === name; })[0] || null; }
function sockOf(tip){ return (tip.lines || []).filter(function(l){ return l.sock; }).map(function(l){ return String(l.html).replace(/<[^>]+>/g, ''); }); }
var ar = d.byName["aldur's rhythm"];
OUT.aldurTip = sockOf(W._cbTipEntry({ id: ar[0], base: ar[3], q: ar[2], affixes: [], eth: false, sockets: 0, rolls: null, ilvl: 99 }, ar, null, null, null));
OUT.aldurRange = W._cbSockRange({ id: ar[0], base: ar[3], ilvl: 99 });
OUT.aldurCap = W._cbMaxSock(ar[3], 99);
var ab = d.byName['blade of ali baba'];
OUT.aliBaba = { fixed: W._cbEntryFor(ab).sockets, cap: W._cbMaxSock(ab[3], 99) };
/* every item with its own numeric socket line: the stepper's range never passes the base, and a range inside it is untouched */
OUT.over = []; OUT.inside = 0; OUT.capped = [];
d.it.forEach(function(it){
  (it[6] || []).forEach(function(l){
    var r = l[3] === 'sock' && l[1] && l[1][0];
    if (!r || typeof r[0] !== 'number' || typeof r[1] !== 'number' || it[2] === 'r') return;
    var cap = W._cbMaxSock(it[3], 99), sr = W._cbSockRange({ id: it[0], base: it[3], ilvl: 99 });
    var lo = Math.min(r[0], r[1]), hi = Math.max(r[0], r[1]);
    if (!(cap > 0)) return;
    if (sr.hi > cap) OUT.over.push(it[1] + ' ' + sr.lo + '-' + sr.hi + ' > ' + cap);
    if (hi <= cap){ if (sr.lo === lo && sr.hi === hi) OUT.inside++; else OUT.over.push(it[1] + ' changed inside its base: ' + sr.lo + '-' + sr.hi); }
    else OUT.capped.push(it[1]);
  });
});
/* a magic item's mod: Jeweler's (Socketed 4) on a Jagged Star, folded into the tooltip's lines */
var jw = Object.keys(d.af).map(function(k){ return d.af[k]; }).filter(function(a){ return (a[11] || []).some(function(l){ return l[3] === 'sock' && l[1][0][0] === 4; }); })[0];
var js = code('Jagged Star'), jsIt = js ? W._cbItem('b:' + js) : null;
OUT.jewel = jw && jsIt ? sockOf(W._cbTipEntry({ id: 'b:' + js, base: js, q: 'm', affixes: [{ id: jw[0], rolls: {} }], eth: false, sockets: 0, rolls: {}, ilvl: 99 }, jsIt, null, null, null)) : 'no fixture';
OUT.jewelUncapped = jw ? W._cbLineHtml((jw[11] || []).filter(function(l){ return l[3] === 'sock'; })[0], {}, null, 'text') : null;
/* the door passes any other line, and a base the database cannot read, unchanged */
var other = ['x', [[5, 10, 'k']], 0, 'str'], sock = ['x', [[2, 5, 'k']], 0, 'sock'];
OUT.door = { other: W._cbSockCapLine(other, js, 99) === other, unread: W._cbSockCapLine(sock, 'no-such-base', 99) === sock,
             capped: W._cbSockCapLine(sock, js, 99)[1][0].slice(0, 2), same: sock[1][0].slice(0, 2) };
})();
"""

SURFACES = {
    "the tooltip": "      l = _cbSockCapLine(l, e.base || it[3], e.ilvl);   /* REG-3071 the base's ceiling */",
    "the stepper's range": "    if (ln) ln = _cbSockCapLine(ln, e.base || it[3], e.ilvl);   /* REG-3071 a range never passes its base */",
    "a fixed count": "(it[6] || []).forEach(function(l){ l = _cbSockCapLine(l, base, e.ilvl); if (l[3] === 'sock'",
    "the Edit tab's lines": "_cbLineHtml(_cbSockCapLine(l, e.base, e.ilvl), e.rolls, clvl, 'edit', slot)",
    "the Edit tab's picked mods": "_cbLineHtml(_cbSockCapLine(l, e.base, e.ilvl), x.rolls || {}, clvl, 'edit', slot)",
    "a d2jsp post's lines": "l = window._cbSockCapLine(l, entry.base || it[3], entry.ilvl);",
}


class ASocketRangeNeverPassesItsBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = None
        if not VPN.NODE:
            return
        cls.out = VPN.run(BODY, prelude="localStorage.setItem('d2r_ownerClaim', '*');\n", timeout=300)

    def setUp(self):
        if self.out is None and self._testMethodName != "test_every_surface_asks_the_one_door":
            self.skipTest("node is absent on this machine - the ranges are UNMEASURED here, never a pass")

    def test_aldurs_rhythm_says_two_to_three(self):
        o = self.out
        self.assertEqual(o["aldurCap"], 3, "the Jagged Star's ceiling moved - re-point this law")
        self.assertEqual(o["aldurTip"], ["Socketed (2-3)"], "the tooltip prints past the Jagged Star's 3")
        self.assertEqual((o["aldurRange"]["lo"], o["aldurRange"]["hi"]), (2, 3))
        self.assertEqual(o["aliBaba"]["fixed"], o["aliBaba"]["cap"], "a fixed count past its base was taken whole")

    def test_no_item_passes_its_base_and_none_inside_is_touched(self):
        o = self.out
        self.assertEqual(o["over"], [], "\n".join(o["over"]))
        self.assertGreater(o["inside"], 20, "the sweep saw almost no socket lines - the fixture is blind")
        self.assertIn("Aldur's Rhythm", o["capped"])

    def test_a_magic_mod_is_capped_too(self):
        self.assertIn("4", str(self.out["jewelUncapped"]), "the fixture's mod no longer says Socketed (4) - re-point this law")
        self.assertEqual(self.out["jewel"], ["Socketed (3)"], "a Jeweler's Jagged Star prints past its base")

    def test_the_door_passes_other_lines(self):
        door = self.out["door"]
        self.assertTrue(door["other"], "the cap touched a line that is not a socket line")
        self.assertTrue(door["unread"], "a base the database cannot read capped a range")
        self.assertEqual((door["capped"], door["same"]), ([2, 3], [2, 5]), "the cap edited the data line itself")

    def test_every_surface_asks_the_one_door(self):
        with open(PAGE, encoding="utf-8") as fh:
            src = fh.read()
        self.assertEqual(src.count("  function _cbSockCapLine(l, code, ilvl){"), 1, "the one door is gone - re-point this law")
        code = re.sub(r"/\*.{0,4000}?\*/", " ", src, flags=re.S)
        bad = [what for what, call in SURFACES.items() if code.count(call.split("   /*")[0]) != 1]
        self.assertEqual(bad, [], "a surface prints an item's socket line without the base's ceiling: %r" % bad)


RED_PROOF = [
    {"why": "REG-3071 - the tooltip prints Aldur's Rhythm Socketed (2-5) again",
     "file": "bible.html",
     "find": "      l = _cbSockCapLine(l, e.base || it[3], e.ilvl);   /* REG-3071 the base's ceiling */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3071 - the socket stepper's range runs past the base",
     "file": "bible.html",
     "find": "    if (ln) ln = _cbSockCapLine(ln, e.base || it[3], e.ilvl);   /* REG-3071 a range never passes its base */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3071 - the door caps nothing (a range inside the base is the only case it keeps)",
     "file": "bible.html",
     "find": "    if (!(cap > 0)) return l;\n    var hi = Math.min(Math.max(r[0], r[1]), cap)",
     "replace": "    if (!(cap > 0) || true) return l;\n    var hi = Math.min(Math.max(r[0], r[1]), cap)",
     "matches": 1, "needs": "node"},
    {"why": "REG-3071 - the d2jsp post's lines skip the door",
     "file": "bible.html",
     "find": "      try { if (typeof window._cbSockCapLine === 'function') l = window._cbSockCapLine(l, entry.base || it[3], entry.ilvl); } catch (eCap) { /* uncapped */ }\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
