# -*- coding: utf-8 -*-
"""REG-2884 (#137, GrokBot v3740 batch: "Stormshield/Lightsabre FIND rows open Mule 1 not M2/M3", then GB 16:08 "FIND-row
click opens NO mule at all") - A FIND ROW OPENS EVERY MULE PAGE ITS COPIES SIT ON.

MEASURED before (whole page in node, a UNI-ARMOR locker filled past one mule by hand adds, his path): no FIND row offered a
mule button. A hand add's cell was swapped for its raw move target, "stash:c0r10 (1,11) target · MANUAL move". That is
row 11 on a 10-row stash: REG-2875 names Mule 2 by that row, and FIND never read it so. That kind of row carried no mule
id either. Stormshield, with copies on Mule 2 and Mule 3, listed both cells and offered no button. REG-2287's button (v3766)
appeared only for a cell that already said "Mule N".

Now a hand add's target reads in FIND's own words ("Mule 2 · Personal stash · col 1 · row 1 · target · MANUAL move"), and
its row carries the target's mule. Each mule page a copy sits on gets one button ("Mule 2", "Mule 3"), and each opens that
locker at that page with the copy drawn. The row itself still opens nothing (#79). A shared stash cell names its page and
gets no mule button. Whole page in node (vault_page_node). Never a browser. RED_PROOF below.
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');\n"
BODY = r"""
var W = window;
function paint(){ W.renderVault(); H.flush(60, 3); }
function row(n){ W.vaultFind(n.toLowerCase()); H.flush(400, 3);
  var h = (document.getElementById('vault-find-results') || {}).innerHTML || '';
  var r = (h.match(/<div class="vfr-row"[\s\S]*?<\/div>(?=<div class="vfr-row"|$)/) || [''])[0];
  var navs = [], re = /window\._muleOpenAt\('([^']*)',(\d+)\)">([^<]*)</g, m;
  while ((m = re.exec(r))) navs.push([m[1], +m[2], m[3]]);
  return { cell: (r.match(/<span class="vfr-cell[^"]*">([^<]*)</) || [])[1] || '', navs: navs, rowClick: /^<div class="vfr-row"[^>]*onclick/.test(r) }; }
function opened(id, pg, n){ W._muleOpenAt(id, pg); H.flush(60, 3);
  var d = (document.getElementById('vault-detail') || {}).innerHTML || '';
  var say = (d.match(/Mule \d+ of \d+/) || [])[0] || null;
  if (W.vaultCloseCard) W.vaultCloseCard(true);
  return { say: say, drawn: d.indexOf('data-vault-item="' + n + '"') >= 0 || d.indexOf('data-key="' + n) >= 0 }; }
W._vaultAutoIntakeSet(false);
var arm = [];
ITEMS.forEach(function(it){ var n = it.name || it.n || it[0]; if (!n || arm.length >= 45) return; var p = null; try { p = W.vaultPropose(n); } catch (e) {}
  if (p && p.ok && p.id === 'uni-armor') arm.push(n); });
arm.forEach(function(n){ W.vaultHandAdd(n); });
W.vaultHandAdd('Stormshield'); W.vaultHandAdd('Stormshield'); W.vaultHandAdd('Stormshield');
W.vaultHandAdd("Death's Fathom");
paint();
OUT.n = arm.length;
var where = {};
arm.forEach(function(n){ var w = W._vaultWhereIs(n); where[n] = w ? String(w.cell || '') : ''; });
var onTwo = arm.filter(function(n){ return /^Mule 2 · Personal stash/.test(where[n]); })[0] || null;
var onOne = arm.filter(function(n){ return /^Mule 1 · /.test(where[n]); })[0] || null;
OUT.onTwo = onTwo; OUT.onOne = onOne;
OUT.storm = row('Stormshield');
OUT.two = onTwo ? row(onTwo) : null;
OUT.one = onOne ? row(onOne) : null;
OUT.fathom = row("Death's Fathom");
OUT.open = {};
(OUT.storm.navs || []).forEach(function(nv){ OUT.open['storm' + nv[2]] = opened(nv[0], nv[1], 'Stormshield'); });
if (OUT.two && OUT.two.navs.length) OUT.open.two = opened(OUT.two.navs[0][0], OUT.two.navs[0][1], onTwo);
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AFindRowOpensEveryMulePageItsCopiesSitOn(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=CLAIM, timeout=900)

    def test_premise_the_locker_spans_three_mules(self):
        o = self.o
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertEqual(o["n"], 45, "PREMISE: %r" % o["n"])
        self.assertTrue(o["onTwo"] and o["onOne"], "PREMISE: no hand add on Mule 1 and Mule 2: %r" % o)

    def test_a_hand_add_names_its_target_by_its_mule_page_and_gets_its_button(self):
        t = self.o["two"]
        self.assertRegex(t["cell"], r"^ · Mule 2 · Personal stash · col \d+ · row \d+ · target · MANUAL move$", t)
        self.assertNotRegex(t["cell"], r"stash:c\d+r\d+", "FIND still prints the raw target cell: %r" % t)
        self.assertEqual([(n[0], n[1], n[2]) for n in t["navs"]], [("uni-armor", 1, "Mule 2")], t)
        self.assertFalse(t["rowClick"], "the row itself opens something again (#79)")
        one = self.o["one"]
        self.assertEqual([n[2] for n in one["navs"]], ["Mule 1"], one)

    def test_copies_on_two_mule_pages_get_a_button_each(self):
        s = self.o["storm"]
        self.assertIn("3 copies: Mule 2", s["cell"], "PREMISE: %r" % s)
        self.assertIn("Mule 3", s["cell"], "PREMISE: %r" % s)
        self.assertEqual([n[2] for n in s["navs"]], ["Mule 2", "Mule 3"], s)

    def test_each_button_opens_that_page_with_the_copy_drawn(self):
        op = self.o["open"]
        self.assertEqual(op.get("stormMule 2"), {"say": "Mule 2 of 3", "drawn": True}, op)
        self.assertEqual(op.get("stormMule 3"), {"say": "Mule 3 of 3", "drawn": True}, op)
        self.assertEqual(op.get("two"), {"say": "Mule 2 of 3", "drawn": True}, op)

    def test_a_shared_stash_cell_names_its_page_and_gets_no_mule_button(self):
        f = self.o["fathom"]
        self.assertIn("Page 1", f["cell"], f)
        self.assertEqual(f["navs"], [], f)


RED_PROOF = [
    {"why": "REG-2884 - FIND prints a hand add's raw target cell (row 11 on a 10-row stash) again",
     "file": "bible.html",
     "find": "cell: _findTargetSay(_mc) + ' · target' + (_ht ? ' · MANUAL move' : '') });",
     "replace": "cell: String(_mc) + ' target' + (_ht ? ' · MANUAL move' : '') });",
     "matches": 1, "needs": "node"},
    {"why": "REG-2884 - a hand add's FIND row carries no mule, so it gets no button",
     "file": "bible.html",
     "find": "w.kind === 'over' || w.kind === 'would' || w.kind === 'target')) ? w.mule : null;",
     "replace": "w.kind === 'over' || w.kind === 'would')) ? w.mule : null;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2884 - copies on two mule pages get one button (the first copy's)",
     "file": "bible.html",
     "find": "_findMuleNavs((w.cells && w.cells.length > 1) ? w.cells : [w.cell])",
     "replace": "_findMuleNavs([w.cell])",
     "matches": 1, "needs": "node"},
    {"why": "REG-2884 - a button opens the locker at Mule 1 whatever page it names",
     "file": "bible.html",
     "find": "window._muleOpenAt(\\''+jsArg(mid)+'\\','+_fnav.index+')\">'+esc(_fnav.label)+'</button>'; }).join('')",
     "replace": "window._muleOpenAt(\\''+jsArg(mid)+'\\',0)\">'+esc(_fnav.label)+'</button>'; }).join('')",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
