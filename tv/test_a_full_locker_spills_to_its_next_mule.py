# -*- coding: utf-8 -*-
"""REG-2875 (his front-run: 300-500 items typed by hand) - A FULL CATEGORY LOCKER SPILLS TO ITS NEXT MULE.

agent-111 measured it (505 hand adds, whole page in node): 81 of 405 copies got a MOVE task with NO cell - SOCKETED 37,
SETS-REST 19, RUNEWORDS 18, UNI-WEAPONS 7. Measured here before the fix on another mix (every catalogue item the router
files on a category locker, 60 runewords): 106 of 232 tasks had no cell - UNI-ARMOR 51, UNI-WEAPONS 49, RUNEWORDS 6. The
MOVE packer filled ONE character per locker (stash 10x10, then inventory 10x4) and dropped the rest, while the mule window
already spreads a locker across Mule 1..N ("+ next mule opens when this one is full"). Only the shared war stash spilled
(to the WAR mules, REG-2803).

Now the packer packs Mule 1, then Mule 2, ... A cell names its Mule by its row, the shared stash's own rule (REG-2801):
stash:c3r14 is Mule 2, col 4, row 5, and inventory rows run 4 per mule. One reader (_vaultCellAt) serves the row, the
expand, the plan and the card. The card lays each task cell on its own Mule k, so the window and the targets agree. The
row reads "UNI-ARMOR · Mule 2 (9,3)". A locker's Mule 2+ is a character he makes in the game (the window's own tip calls
them "mule characters"), and it is derived, not a roster entry. So MOVE TASKS asks him first to create it, as REG-2803 does
for WAR1, and his tick is kept on the locker's entry. Saved targets never move (REG-2787): only copies with no saved cell
are placed. Whole page in node, never a browser. RED_PROOF below.
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
BASES = ["Monarch", "Phase Blade", "Thresher", "Archon Plate", "Dusk Shroud", "Sacred Targe", "Berserker Axe", "Giant Thresher"]

LIB = r"""
var W = window;
function recs(){ return (JSON.parse(W.LSR.getItem('d2r_vaultRecords') || '{}').records || []).filter(function(r){ return r && r.move && r.move.to && r.move.kind !== 'throw'; }); }
function targets(){ var o = {}; recs().forEach(function(r){ o[r.name + '#' + (r.copyIx || 0)] = [r.move.to.id == null ? null : r.move.to.id, r.move.to.cell || null]; }); return o; }
function list(){ return (document.getElementById('vault-move-list') || {}).innerHTML || ''; }
function paint(){ W.renderVault(); H.flush(60, 3); }
"""

BODY = LIB + r"""
W._vaultAutoIntakeSet(false);
var names = [];
ITEMS.forEach(function(it){ var n = it.name || it.n || it[0]; if (!n) return; var pg = null; try { pg = W.vaultPropose(n); } catch (e) {}
  if (pg && pg.ok && pg.kind === 'mule' && pg.id !== 'shared') names.push(n); });
var rw = []; try { rw = RUNEWORDS.map(function(r){ return r.name || r.n || r[0]; }).filter(Boolean).slice(0, 60); } catch (e) {}
var bases = %(bases)s, adds = names.concat(rw);
bases.forEach(function(b){ for (var i = 0; i < 6; i++) adds.push(b); });
adds.forEach(function(n){ W.vaultHandAdd(n); });
paint();
OUT.adds = adds.length;
var rs = recs(), byId = {};
OUT.tasks = rs.length;
OUT.nocell = rs.filter(function(r){ return !r.move.to.cell; }).map(function(r){ return [r.name, r.move.to.holder]; });
rs.forEach(function(r){ var t = r.move.to, ca = W._vaultCellAt(t.cell); if (!ca || t.id == null || t.id === 'shared' || t.id === 'main') return;
  if (W._vaultWarMules().some(function(w){ return w.id === t.id; })) return;   /* a WAR mule is the war stash's overflow, one page */
  (byId[t.id] = byId[t.id] || []).push({ n: r.name, ci: r.copyIx || 0, loc: ca.loc, page: ca.page, x: ca.x, y: ca.y }); });
OUT.byId = byId;
OUT.names = {};
Object.keys(byId).forEach(function(id){ byId[id].forEach(function(t){ if (!OUT.names[t.n]) { var w = W._vaultWhereIs(t.n); OUT.names[t.n] = w ? (w.cells || []) : null; } }); });
OUT.rows = (list().match(/<span class="vtk-to">[^<]*/g) || []).map(function(s){ return s.replace('<span class="vtk-to">', ''); });
OUT.make = (list().match(/<li class="vtk-line vtk-make"[^>]*data-page="\d+"[\s\S]*?<\/li>/g) || []).map(function(x){ return [(x.match(/data-mule="([^"]*)"/) || [])[1], (x.match(/data-page="(\d+)"/) || [])[1], x.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()]; });
OUT.before = targets();
// his tick on the first make row, then more items arrive
if (OUT.make.length) { OUT.tick = W._vaultPageMadeInGame(OUT.make[0][0], +OUT.make[0][1]); paint();
  OUT.afterTick = (list().match(/data-page="\d+"/g) || []).length;
  OUT.made = (JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return m.id === OUT.make[0][0]; })[0] || {}).pagesMade || null; }
bases.forEach(function(b){ for (var i = 0; i < 3; i++) W.vaultHandAdd(b); });
['Death\'s Fathom', 'Windforce', 'Eaglehorn'].forEach(function(n){ W.vaultHandAdd(n); });
paint();
OUT.after = targets();
OUT.nocellAfter = recs().filter(function(r){ return !r.move.to.cell; }).length;
OUT.rects = recs().map(function(r){ var t = r.move.to, ca = W._vaultCellAt(t.cell), s = W.vaultSize(r.name);
  return ca ? [String(t.id), ca.loc, ca.page, ca.x, ca.y, s[0] || 1, s[1] || 1, r.name + '#' + (r.copyIx || 0)] : null; }).filter(Boolean);
""" % {"bases": json.dumps(BASES)}


def _expected(t, spans):
    where = "Personal stash" if t["loc"] == "stash" else "Inventory"
    return ("Mule %d · " % (t["page"] + 1) if spans else "") + "%s · col %d · row %d" % (where, t["x"] + 1, t["y"] + 1)


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AFullLockerSpillsToItsNextMule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=CLAIM, timeout=900)

    def test_every_copy_gets_a_cell(self):
        o = self.o
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertGreater(o["tasks"], 250, "PREMISE: the mix made too few tasks: %r" % o["tasks"])
        self.assertTrue(any(t["page"] >= 1 for ts in o["byId"].values() for t in ts), "PREMISE: no locker filled its first mule")
        self.assertEqual(o["nocell"], [], "copies got a MOVE task with no cell: %d, e.g. %r" % (len(o["nocell"]), o["nocell"][:5]))
        self.assertEqual(o["nocellAfter"], 0)

    def test_the_card_draws_every_copy_at_its_task_cell_on_its_mule(self):
        o, bad = self.o, []
        for mid, ts in o["byId"].items():
            spans = any(t["page"] >= 1 for t in ts)
            for n in set(t["n"] for t in ts):
                want = sorted(_expected(t, spans) for t in ts if t["n"] == n)
                have = list(o["names"].get(n) or [])
                for w in want:
                    if w in have:
                        have.remove(w)
                    else:
                        bad.append((mid, n, w, o["names"].get(n)))
        self.assertEqual(bad, [], "the card and the targets disagree on %d copies, e.g. %r" % (len(bad), bad[:3]))

    def test_the_row_names_the_mule(self):
        rows = [r for r in self.o["rows"] if " · Mule " in r]
        self.assertTrue(rows, "no row names a Mule 2+: %r" % self.o["rows"][:5])
        for r in rows:
            self.assertRegex(r, r"^[A-Z][A-Z\-]+ · Mule [2-9]\d* \(\d+,\d+\)$", r)

    def test_he_is_tasked_to_make_the_next_mule_and_his_tick_is_kept(self):
        o = self.o
        self.assertTrue(o["make"], "MOVE TASKS does not ask him to make a locker's next mule")
        mid, page, text = o["make"][0]
        self.assertEqual(page, "2")
        self.assertRegex(text, r"Create mule [A-Z][A-Z\-]+ #2 in the game")
        self.assertEqual(o["tick"], {"ok": True}, o["tick"])
        self.assertEqual(o["made"], [2], "his tick was not kept on the locker: %r" % o["made"])
        self.assertEqual(o["afterTick"], len(o["make"]) - 1, "the made mule is still asked for")

    def test_saved_targets_never_move_and_never_overlap(self):
        o = self.o
        moved = [(k, v, o["after"].get(k)) for k, v in o["before"].items() if o["after"].get(k) != v]
        self.assertEqual(moved, [], "more items moved saved targets: %r" % moved[:5])
        self.assertGreater(len(o["after"]), len(o["before"]), "PREMISE: the second batch added nothing")
        by, hits = {}, []
        for mid, loc, pg, x, y, w, h, key in o["rects"]:
            by.setdefault((mid, loc, pg), []).append((x, y, w, h, key))
        for L in by.values():
            for i in range(len(L)):
                for j in range(i + 1, len(L)):
                    a, b = L[i], L[j]
                    if a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]:
                        hits.append((a[4], b[4]))
        self.assertEqual(hits, [], "two targets overlap: %r" % hits[:4])


RED_PROOF = [
    {"why": "REG-2875 - a full locker drops its rest again (one mule only)",
     "file": "bible.html",
     "find": "    while (leftN.length && pgN < 40) {\n",
     "replace": "    while (leftN.length && pgN < 1) {\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2875 - the plan drops the Mule of a task cell, so the card draws a Mule 2 copy on Mule 1",
     "file": "bible.html",
     "find": "page: _vaultCellAt(to.cell).page, x: +c[2], y: _vaultCellAt(to.cell).y });   /* REG-2875 Mule k */",
     "replace": "page: 0, x: +c[2], y: _vaultCellAt(to.cell).y });   /* REG-2875 Mule k */",
     "matches": 1, "needs": "node"},
    {"why": "REG-2875 - the card lays every planned copy on Mule 1",
     "file": "bible.html",
     "find": "        var _plPg = (pl && pl.page > 0) ? pl.page : 0;   /* REG-2875 a task cell on Mule k is drawn on Mule k */\n",
     "replace": "        var _plPg = 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2875 - the row does not name the Mule",
     "file": "bible.html",
     "find": "      if (_ca && _ca.page > 0) return h + ' · Mule ' + (_ca.page + 1) + ' (' + (_ca.x + 1) + ',' + (_ca.y + 1) + ')';   /* REG-2875 the next mule of a full locker */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2875 - a page's saved cells are not taken before it packs (a new item lands on a saved target)",
     "file": "bible.html",
     "find": "      return (occBy[loc] || []).filter(function(r){ return r.y >= pgN * rows && r.y < (pgN + 1) * rows; })\n",
     "replace": "      return [].filter(function(r){ return r.y >= pgN * rows && r.y < (pgN + 1) * rows; })\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2875 - he is not asked to make a locker's next mule",
     "file": "bible.html",
     "find": "      for (var p = 1; p <= top[id]; p++) if (made.indexOf(p + 1) < 0) rows.push({ id: m.id, mule: p + 1, name: m.name });\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2875 - his tick on a made mule is not kept",
     "file": "bible.html",
     "find": "    m.pagesMade = (was || []).filter(function(x){ return x !== k; }).concat([k]);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2875 - the cell reader reads inventory rows as stash rows (Mule 2 of an inventory is lost)",
     "file": "bible.html",
     "find": "    var rows = m[1] === 'inventory' ? 4 : 10, y = +m[3];\n",
     "replace": "    var rows = 10, y = +m[3];\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
