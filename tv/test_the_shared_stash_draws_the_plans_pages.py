# -*- coding: utf-8 -*-
"""#144.10 shared half (REG-2801, REG-2802, his ruling 2026-10-28) - THE SHARED STASH IS DRAWN AS ITS MOVE TASKS LAY IT: 5 PAGES, THEN
THE WAR MULES.

His words: "the war stash is basically the shared stash with those 5 pages + the extra war mules if they get full that
should open already automatically if that happens". MEASURED before (node, whole page; Shako x3 + Arachnid Mesh x6 hand-
added, a WAR1 mule): the move tasks put Shako 1 at shared:c0r0 (page 1, col 1, row 1) and belts 1-4 on page 1, the over-
cap copies on WAR1; the window opened on its "Weapons" tab with nothing on it, drew the Shako on "Armor · Helms · Shields"
and the belts on "Gloves · Belts · Boots" (#264's by-slot tabs), counted 9 copies though 4 are WAR1's, and FIND named
those tabs - for all 3 Shakos and all 6 belts. And past the 5 pages: 505 copies of an uncapped ring filled pages 1-5 and the
plan sent 5 to WAR1, which no window drew and no FIND named (_vaultWarOverOn counted only over-cap copies).

Now one layout, _sharedLayout: each copy at the page and cell its task names (the k-th copy at the k-th shared task cell,
_vaultPlanOn('shared')), a copy with no task packed after them page 1 first, and the copies the war cap keeps there (the
count the shelf card already drew). The window, FIND (filed and would answers, plus the WAR mules' copies) and the
organizer read it; a WAR mule draws every copy the plan puts on it. Overflow past the 5 pages goes to WAR1, WAR2 ... on its
own; since REG-2803 (his ruling 2026-10-28) the board makes the WAR mule when there is none, so the world below with no WAR
mule ends with the board's WAR1 holding the 5 rings past the pages.

Driven on the whole page in node (vault_page_node - never a browser on his Mac). RED_PROOF below.
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
SHAKO, BELT, CROWN, SOJ, WAR = "Harlequin Crest (Shako)", "Arachnid Mesh", "Crown of Ages", "The Stone of Jordan", "war-law-0"
TYPED = ("Weapons", "Armor · Helms · Shields", "Gloves · Belts · Boots", "Rings · Amulets · Charms", "Spare · slot unknown")

BODY_WAR = r"""
var W = window, NAMES = [%(shako)s, %(belt)s];
W._vaultAutoIntakeSet(false);
OUT.add = [%(shako)s, %(shako)s, %(shako)s, %(belt)s, %(belt)s, %(belt)s, %(belt)s, %(belt)s, %(belt)s]
  .map(function(n){ return !!(W.vaultHandAdd(n) || {}).ok; });
W.vaultAssign(%(belt)s, 'shared');          /* the belt takes FIND's filed answer, the Shako its would answer */
W.renderVault(); H.flush(60, 3);
OUT.tasks = {};
NAMES.forEach(function(n){ OUT.tasks[n] = []; for (var ci = 0; ci < copyCount(n); ci++) {
  var t = (W._vaultMoveEnsure(n, ci) || {}).task; OUT.tasks[n].push(t && t.to ? [t.to.id || null, t.to.cell || null] : null); } });
var lay = W._sharedLayout(W._sharedDrawNames());
OUT.pages = lay.pages.map(function(p){ return p.map(function(q){ return [q.n, q.key, q.x, q.y]; }); });
OUT.left = lay.left.length;
OUT.fault = W._gridFault(lay.pages[0], 10, 10);
W.openMuleCard('shared');
var h = (document.getElementById('vault-detail') || {}).innerHTML || '';
OUT.list = []; var re = /<div>([^<]+) → <span class="vl-slot">([^<]+)<\/span>/g, m; while ((m = re.exec(h))) OUT.list.push([m[1], m[2]]);
OUT.tabs = []; var rt = /role="tab"[^>]*>([^<]+)/g; while ((m = rt.exec(h))) OUT.tabs.push(m[1].trim());
OUT.windowHtml = h;
OUT.find = {}; NAMES.forEach(function(n){ var w = W._vaultWhereIs(n); OUT.find[n] = w ? { kind: w.kind, cells: w.cells || [] } : null; });
var shelf = (document.getElementById('vault-shelf') || {}).innerHTML || '';
var at = shelf.indexOf('data-vault-mule="shared"'), nx = at < 0 ? -1 : shelf.indexOf('data-vault-mule="', at + 10);
var card = at < 0 ? '' : shelf.slice(at, nx < 0 ? shelf.length : nx);
OUT.card = {}; NAMES.concat([%(crown)s]).forEach(function(n){ OUT.card[n] = card.split('data-vault-item="' + n.replace(/'/g, '&#39;') + '"').length - 1; });
OUT.org = W._orgPlannedCells([{ nm: 'Raven Frost', pg: { ok: true, kind: 'mule', id: 'shared' } }]).cells;
W.renderVault(); H.flush(60, 3);
OUT.rows = []; var rr = /→ (SHARED STASH [^"<]*?(?:\(\d+,\d+\)|Page \d+ · col \d+ · row \d+))/g, mr, ml = (document.getElementById('vault-move-list') || {}).innerHTML || '';   /* REG-3005 the one spelling (the old "(x,y)" kept so a revert is read, and refused) */
while ((mr = rr.exec(ml))) if (OUT.rows.indexOf(mr[1]) < 0) OUT.rows.push(mr[1]);
"""

BODY_SOJ = r"""
var W = window, n = %(soj)s;
W.renderVault(); H.flush(60, 3);
OUT.copies = copyCount(n);
OUT.plan = {}; for (var i = 0; i < copyCount(n); i++) { var t = (W._vaultMoveEnsure(n, i) || {}).task, to = t && t.to;
  var k = !to || !to.cell ? 'none' : (to.id === 'shared' ? 'page ' + (Math.floor(+String(to.cell).match(/r(\d+)$/)[1] / 10) + 1) : (to.holder || to.id)); OUT.plan[k] = (OUT.plan[k] || 0) + 1; }
var lay = W._sharedLayout(W._sharedDrawNames());
OUT.pages = lay.pages.map(function(p){ return p.length; }); OUT.left = lay.left.length;
var _w1 = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return W._vaultWarRole(m) === 1; })[0] || null;   /* REG-2980 war mule 1 by number */
OUT.war1 = _w1 ? { id: _w1.id, auto: (_w1.auto || {}).by || null } : null;
OUT.w1name = _w1 ? _w1.name : null;
var L = _w1 ? W._muleLoad(W._muleNamesFor(_w1.id), {}, _w1.id) : { phys: 0 }; OUT.warDraws = L.phys;
var w = W._vaultWhereIs(n); OUT.findN = (w.cells || []).length; OUT.findWar = (w.cells || []).filter(function(c){ return c.indexOf(OUT.w1name + ' · ') === 0; }).length;
W.openMuleCard('shared'); var h = (document.getElementById('vault-detail') || {}).innerHTML || '';
OUT.note = ((h.match(/<div class="vd-overflow"[^>]*>([\s\S]*?)<\/div>/) || [])[1] || '').replace(/<[^>]+>/g, '');
OUT.roster = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').map(function(m){ return m.name; });
/* REG-2802 - copy 121 sits on page 2: the row's expand must read its cell as that page's */
var t2 = (W._vaultMoveEnsure(n, 120) || {}).task; OUT.cell120 = t2 && t2.to && t2.to.cell;
var hx = W._vaultTaskExpandHtml(n, 120), ix = hx.indexOf('class="vtx-to"');
var tl = /data-x="(\d+)" data-y="(\d+)"/.exec(hx.slice(ix)); OUT.expandTile = tl ? [+tl[1], +tl[2]] : null;
OUT.expandGrid = (/data-gw="(\d+)" data-gh="(\d+)"/.exec(hx.slice(ix)) || []).slice(1).map(Number);
OUT.expandHead = ((hx.slice(ix).match(/<div class="vtx-h">([^<]*)/) || [])[1] || '');
OUT.find120 = (w.cells || [])[120] || null;
"""


def _fmt(body):
    return body % {"shako": json.dumps(SHAKO), "belt": json.dumps(BELT), "crown": json.dumps(CROWN),
                   "soj": json.dumps(SOJ), "war": json.dumps(WAR)}


def _cell(c):
    """'shared:c3r12' -> (page index, x, y) on that page."""
    m = re.match(r"^shared:c(\d+)r(\d+)$", c or "")
    return (int(m.group(2)) // 10, int(m.group(1)), int(m.group(2)) % 10) if m else None


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheSharedStashDrawsThePlansPages(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        base = VPN.run("OUT.r = JSON.parse(window.LSR.getItem('d2r_muleRoster') || 'null') || "
                       "(window._vaultRosterNow && window._vaultRosterNow());", prelude=CLAIM, timeout=300).get("r")
        if not isinstance(base, list) or not base:
            raise AssertionError("PREMISE: the page has no default roster to extend: %r" % (base,))
        plain = [m for m in base if not str(m.get("id", "")).startswith("war-law-")]
        war = CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n" % json.dumps(json.dumps(plain + [{"id": WAR, "name": "WAR1"}]))
        nowar = CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n" % json.dumps(json.dumps(plain))
        crown = ("localStorage.setItem('d2r_owned', %s);\nlocalStorage.setItem('d2r_muleAssign', %s);\n"
                 % (json.dumps(json.dumps([CROWN])), json.dumps(json.dumps({CROWN: "shared"}))))
        rings = ("localStorage.setItem('d2r_owned', %s);\nlocalStorage.setItem('d2r_copies', %s);\n"
                 % (json.dumps(json.dumps([SOJ])), json.dumps(json.dumps({SOJ: 505}))))
        cls.w = VPN.run(_fmt(BODY_WAR), prelude=war + crown, timeout=300)
        cls.s = VPN.run(_fmt(BODY_SOJ), prelude=war + rings, timeout=600)
        cls.n = VPN.run(_fmt(BODY_SOJ), prelude=nowar + rings, timeout=600)

    def _shared_tasks(self, name):
        return [c for (i, c) in (self.w["tasks"][name] or []) if i == "shared"]

    def test_the_premise_five_copies_go_to_page_one_and_four_to_war1(self):
        w = self.w
        self.assertEqual(w["__boot"]["errors"], [], w["__boot"])
        self.assertTrue(all(w["add"]), "PREMISE: a hand add did not land: %r" % w["add"])
        self.assertEqual((len(self._shared_tasks(SHAKO)), len(self._shared_tasks(BELT))), (1, 4), "PREMISE: %r" % w["tasks"])
        war = [c for n in (SHAKO, BELT) for (i, c) in w["tasks"][n] if i == WAR]
        self.assertEqual(len(war), 4, "PREMISE: not four copies bound for WAR1: %r" % w["tasks"])

    def test_each_copy_is_drawn_at_the_page_and_cell_its_task_names(self):
        drawn = {}
        for pi, page in enumerate(self.w["pages"]):
            for n, key, x, y in page:
                drawn.setdefault(n, []).append((pi, x, y))
        for n in (SHAKO, BELT):
            want = [_cell(c) for c in self._shared_tasks(n)]
            self.assertEqual(drawn.get(n), want, "%s: the shared stash draws %r, its tasks say %r" % (n, drawn.get(n), want))

    def test_the_stash_keeps_what_the_war_cap_keeps_and_a_copy_with_no_task_fills_page_one(self):
        w = self.w
        self.assertEqual(sum(len(p) for p in w["pages"]), 6, "the shared stash does not draw Shako 1 + belts 4 + the Crown: %r" % w["pages"])
        self.assertEqual([p for p in w["pages"][1:] if p], [], "a copy went past page 1 with page 1 nearly empty: %r" % w["pages"])
        self.assertEqual([n for n, k, x, y in w["pages"][0]].count(CROWN), 1, "the Crown (filed, no task) is not on page 1")
        self.assertFalse(w["fault"]["fault"], "two copies share a cell on page 1: %r" % w["fault"])
        self.assertEqual(w["left"], 0, w)

    def test_the_window_draws_the_pages_and_says_each_copys_cell(self):
        w = self.w
        self.assertEqual(w["tabs"], ["Page %d" % i for i in range(1, 6)], "the shared stash's tabs are not its 5 pages: %r" % w["tabs"])
        for label in TYPED:
            self.assertNotIn(label, w["windowHtml"], "the window still lays the stash by slot (%r)" % label)
        for n in (SHAKO, BELT):
            for c in self._shared_tasks(n):
                pg, x, y = _cell(c)
                self.assertIn([n, "Page %d · col %d · row %d" % (pg + 1, x + 1, y + 1)], w["list"],   # REG-3005 the one spelling
                              "the window does not say %s sits where its task sends it (%s): %r" % (n, c, w["list"]))

    def test_find_names_the_page_cells_and_the_war_mules_copies(self):
        w = self.w
        for n in (SHAKO, BELT):
            f = w["find"][n] or {}
            page = ["Page %d · col %d · row %d" % (pg + 1, x + 1, y + 1) for pg, x, y in (_cell(c) for c in self._shared_tasks(n))]
            war = ["WAR1 · Personal stash · col %d · row %d" % (int(m.group(1)) + 1, int(m.group(2)) + 1)
                   for m in (re.match(r"^stash:c(\d+)r(\d+)$", c or "") for (i, c) in w["tasks"][n] if i == WAR) if m]
            self.assertEqual(sorted(f.get("cells") or []), sorted(page + war),
                             "%s (%s answer): FIND names %r, the plan says %r" % (n, f.get("kind"), f.get("cells"), page + war))
        self.assertEqual(w["find"][BELT]["kind"], "filed", "PREMISE: the belt did not take FIND's filed answer")
        self.assertEqual(w["find"][SHAKO]["kind"], "would", "PREMISE: the Shako did not take FIND's would answer")

    def test_the_shelf_card_and_the_organizer_agree(self):
        w = self.w
        self.assertEqual(w["card"], {SHAKO: 1, BELT: 4, CROWN: 1}, "the shared card draws other copies than the window: %r" % w["card"])
        self.assertRegex((w["org"] or {}).get("Raven Frost") or "", r"^Page \d · col \d+ · row \d+$",
                         "the organizer names no page cell for an item planned to the shared stash: %r" % w["org"])

    def test_past_the_five_pages_war1_takes_the_rest_and_draws_them(self):
        s = self.s
        self.assertEqual(s["__boot"]["errors"], [], s["__boot"])
        self.assertEqual(s["plan"], {"page 1": 100, "page 2": 100, "page 3": 100, "page 4": 100, "page 5": 100, "WAR1": 5},
                         "PREMISE: the plan did not fill the 5 pages and send the rest to WAR1: %r" % s["plan"])
        self.assertEqual((s["pages"], s["left"]), ([100] * 5, 5), s)
        self.assertEqual(s["warDraws"], 5, "WAR1's window does not draw the 5 copies the plan sent it: %r" % s)
        self.assertEqual((s["findN"], s["findWar"]), (505, 5), "FIND does not name every copy, WAR1's among them: %r" % s)
        self.assertIn("(WAR1)", s["note"], "the overflow note does not name the WAR mule that takes them: %r" % s["note"])

    def test_with_no_war_mule_the_board_makes_war1_and_the_rest_go_there(self):
        """REG-2803 (his ruling 2026-10-28): with no WAR mule the board makes WAR1; the 5 rings past the pages land on it, its
        window draws them, and the note names it."""
        n = self.n
        self.assertEqual(n["plan"], {"page 1": 100, "page 2": 100, "page 3": 100, "page 4": 100, "page 5": 100, n["w1name"]: 5},
                         "the 5 rings past the pages did not land on the board's war mule 1: %r" % n["plan"])
        self.assertEqual([r for r in n["roster"] if re.match(r"^war", str(r), re.I)], [n["w1name"]], "not exactly one WAR mule: %r" % n["roster"])
        self.assertEqual((n["war1"] or {}).get("auto"), "board", "WAR1 was not made by the board: %r" % n["war1"])
        self.assertEqual(n["warDraws"], 5, n)
        self.assertIn("(%s)" % n["w1name"], n["note"], "the overflow note does not name the board's war mule 1: %r" % n["note"])


    def test_the_move_row_and_its_expand_name_the_page_and_cell_find_names(self):
        """REG-2802 - the row said "tab" while the window and FIND said "Page" for the same cell, and a page-2 task's expand
        read the shared cell raw: "(1,13)", its tile on row 12 of a 10x10 grid."""
        w = self.w
        for n in (SHAKO, BELT):
            for c in self._shared_tasks(n):
                pg, x, y = _cell(c)
                self.assertIn("SHARED STASH · Page %d · col %d · row %d" % (pg + 1, x + 1, y + 1), w["rows"],   # REG-3005
                              "the move row does not name %s's page and cell (%s): %r" % (n, c, w["rows"]))
                self.assertIn("Page %d · col %d · row %d" % (pg + 1, x + 1, y + 1), w["find"][n]["cells"])
        self.assertFalse([r for r in w["rows"] if " tab " in r], "a move row still says tab: %r" % w["rows"])
        s = self.s
        pg, x, y = _cell(s["cell120"])
        self.assertEqual(pg, 1, "PREMISE: copy 121 of 505 rings is not on page 2: %r" % s["cell120"])
        self.assertEqual(s["find120"], "Page %d · col %d · row %d" % (pg + 1, x + 1, y + 1), s)
        self.assertIn("SHARED STASH · Page %d · col %d · row %d" % (pg + 1, x + 1, y + 1), s["expandHead"],   # REG-3005
                      "the expand names another cell than the row and FIND: %r" % s["expandHead"])
        self.assertEqual(s["expandTile"], [x, y], "the expand draws the copy off its page's cell: %r" % s)
        self.assertTrue(s["expandTile"][1] < s["expandGrid"][1], "the expand's tile is off its %r grid: %r" % (s["expandGrid"], s["expandTile"]))


RED_PROOF = [
    {"why": "REG-2801 - the plan reader skips the shared stash again (the window and FIND pack by size, not by task)",
     "file": "bible.html",
     "find": "    if (muleId == null || typeof _vaultMoveBag !== 'function') return null;\n",
     "replace": "    if (muleId == null || muleId === 'shared' || typeof _vaultMoveBag !== 'function') return null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - a shared task cell is not read as a page and a cell",
     "file": "bible.html",
     "find": "      var c = String(to.cell).match(/^(stash|inventory|shared):c(\\d+)r(\\d+)$/);\n",
     "replace": "      var c = String(to.cell).match(/^(stash|inventory):c(\\d+)r(\\d+)$/);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - the shared stash draws every copy, the WAR mules' among them",
     "file": "bible.html",
     "find": "      try { cc = _shelfCopyCount(n, 'shared'); } catch (eC) { cc = 1; }\n",
     "replace": "      try { cc = copyCount(n); } catch (eC) { cc = 1; }\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - the window says another page than the one it draws",
     "file": "bible.html",
     "find": "' → <span class=\"vl-slot\">' + esc(_sharedSpotSay(_sharedPage, p.x, p.y))",
     "replace": "' → <span class=\"vl-slot\">' + esc(_sharedSpotSay(_sharedPage + 1, p.x, p.y))",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - FIND's filed answer leaves the WAR mules' copies out",
     "file": "bible.html",
     "find": "          _vaultWarCellsOf(nm, _put);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - FIND's would answer leaves the WAR mules' copies out",
     "file": "bible.html",
     "find": "          _vaultWarCellsOf(nm, _putW);\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - a WAR mule counts only over-cap copies again (page overflow is drawn nowhere)",
     "file": "bible.html",
     "find": "      for (var i = 0; i < cc; i++) {\n        var pl = _vaultMovePlanCell(n, i);\n",
     "replace": "      for (var i = 0; i < cc; i++) {\n        if (!_vaultWarOver(n, i)) continue;\n        var pl = _vaultMovePlanCell(n, i);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - the overflow note says there is no WAR1 when there is one",
     "file": "bible.html",
     "find": "      + (wars.length\n          ? 'Past them",
     "replace": "      + (false\n          ? 'Past them",
     "matches": 1, "needs": "node"},
    {"why": "REG-2801 - the organizer names a cell from another layout than the window's",
     "file": "bible.html",
     "find": "            if (planned.indexOf(q.n) >= 0 && !cells[q.n]) cells[q.n] = _sharedSpotSay(pi, q.x, q.y); }); });   /* REG-3005 */\n",
     "replace": "            if (planned.indexOf(q.n) >= 0 && !cells[q.n]) cells[q.n] = 'Weapons tab · col ' + (q.x + 1) + ' · row ' + (q.y + 1); }); });\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2802 - the move row says tab while the window and FIND say page",
     "file": "bible.html",
     "find": "        return h + ' · ' + _sharedSpotSay(Math.floor((+m[2]) / 10), +m[1], (+m[2]) % 10);   /* REG-3005 the one spelling */",
     "replace": "        return h + ' tab ' + (Math.floor((+m[2]) / 10) + 1) + ' (' + ((+m[1]) + 1) + ',' + ((+m[2]) % 10 + 1) + ')';",
     "matches": 1, "needs": "node"},
    {"why": "REG-2802 - the expand reads a shared cell raw (row 13 of a 10-row page, the tile off the grid)",
     "file": "bible.html",
     "find": "      return m[1] === 'shared' ? { loc: m[1], x: +m[2], y: +m[3] % 10, page: Math.floor(+m[3] / 10) } : { loc: m[1], x: ca.x, y: ca.y, mule: ca.page }; }",
     "replace": "      return { loc: m[1], x: +m[2], y: +m[3] }; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-2802 - the expand's words drop the page",
     "file": "bible.html",
     "find": "      if (c.page != null) return nm + ' · ' + _sharedSpotSay(c.page, c.x, c.y);   /* REG-3005 a shared page cell in the one spelling */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
