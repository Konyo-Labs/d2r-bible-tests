# -*- coding: utf-8 -*-
"""#144.10 (REG-2782, GrokBot's eyes-pass A1, seeds 1012 / 1013 / 1021 - "almost all batches") - A MULE CARD DRAWS A COPY
WHERE ITS MOVE TASK SENDS IT.

GrokBot: "SOCKETED tasks are Monarch c0r0, Phase Blade c4r0, Thresher c5r0, but the open card draws Thresher (0,0) and
Monarch (4,0) ... the card re-packs with packGrid (largest first) while tasks use append-only targets". Measured here
before the fix (node, whole page): Gull, The Grandfather and Lightsabre added by hand get tasks stash:c0r0 / c1r0 / c3r0
on UNI-WEAPONS; the card drew them at (4,0) / (0,0) / (2,0), and FIND - which asks the card's packer - named the card's
cells, not the tasks'. A task's cell is append-only (Elad ruling 1), so every later, bigger arrival slid the card away
from the cells he was told to use.

Now _muleLoad lays the k-th copy of a name at the k-th task cell saved on that locker (_vaultPlanOn), after his own hand
spots; a task cell that is taken packs as before, and a copy with no task packs exactly as it did. The WAR mules follow
the same rule (with REG-2781 their over-cap copies are drawn at all).

NOT in this fix (reported): the SHARED STASH window lays war gear by typed tabs (Armor / Weapons / ...) while its tasks
name pages of a fill order ("shared:c0r0", page 1); which of the two is the war stash's layout is his call.

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
WEAP = ["Gull (dagger)", "The Grandfather", "Lightsabre"]   # 1x2, 2x4, 2x3: the planner's append order is not largest-first
FILED = "The Gnasher"                                       # filed on UNI-WEAPONS with no task: packs as it always did
WAR, SHAKO, BELT = "war-law-0", "Harlequin Crest (Shako)", "Arachnid Mesh"

READ = r"""
function cells(L){
  var out = [];
  (L.mules || []).forEach(function(m, pg){
    (m.stash || []).forEach(function(p){ out.push({ n: p.n, key: p.key, at: pg === 0 ? 'stash:c' + p.x + 'r' + p.y : 'mule' + pg, w: p.w, h: p.h, hand: !!p.manual }); });
    (m.inv || []).forEach(function(p){ out.push({ n: p.n, key: p.key, at: pg === 0 ? 'inventory:c' + p.x + 'r' + p.y : 'mule' + pg, w: p.w, h: p.h, hand: !!p.manual }); });
  });
  return out;
}
function tasks(names){
  var out = {};
  names.forEach(function(n){
    var cc = (typeof copyCount === 'function') ? copyCount(n) : 1;
    for (var ci = 0; ci < cc; ci++) { var t = (window._vaultMoveEnsure(n, ci) || {}).task; (out[n] = out[n] || []).push(t && t.to ? { id: t.to.id || null, cell: t.to.cell || null } : null); }
  });
  return out;
}
function load(mid){ return window._muleLoad(window._muleNamesFor(mid), {}, mid); }
"""

BODY_WEAP = READ + r"""
var W = window; W._vaultAutoIntakeSet(false);
OUT.add = [!!(W.vaultHandAdd(%(w0)s) || {}).ok];
W.renderVault(); H.flush(60, 3);        /* a paint between the adds: the card reads the store again after it changed */
OUT.add.push(!!(W.vaultHandAdd(%(w1)s) || {}).ok, !!(W.vaultHandAdd(%(w2)s) || {}).ok);
W.renderVault(); H.flush(60, 3);
OUT.tasks = tasks(%(weap)s);
var L = load('uni-weap');
OUT.cells = cells(L); OUT.fault = W._gridFault((L.mules[0] || {}).stash || [], 10, 10);
OUT.find = {};
%(weap)s.forEach(function(n){ var w = W._vaultWhereIs(n); OUT.find[n] = w ? (w.cells || []) : null; });
"""

BODY_WAR = READ + r"""
var W = window; W._vaultAutoIntakeSet(false);
OUT.add = %(adds)s.map(function(n){ return !!(W.vaultHandAdd(n) || {}).ok; });
W.renderVault(); H.flush(60, 3);
OUT.tasks = tasks([%(shako)s, %(belt)s]);
OUT.cells = cells(load(%(war)s));
"""

BODY_HAND = READ + r"""
var W = window; W._vaultAutoIntakeSet(false);
OUT.add = %(weap)s.map(function(n){ return !!(W.vaultHandAdd(n) || {}).ok; });
W.renderVault(); H.flush(60, 3);
OUT.tasks = tasks(%(weap)s);
var L = load('uni-weap');
OUT.cells = cells(L); OUT.fault = W._gridFault((L.mules[0] || {}).stash || [], 10, 10); OUT.conflicts = (L.conflicts || []).length;
"""

BODY_NINE = READ + r"""
var W = window; W._vaultAutoIntakeSet(false);
OUT.add = []; for (var i = 0; i < 9; i++) OUT.add.push(!!(W.vaultHandAdd("The Grandfather") || {}).ok);
W.renderVault(); H.flush(60, 3);
OUT.tasks = tasks(["The Grandfather"]);
var L = load('uni-weap');
OUT.cells = cells(L); OUT.room = L.roomLeft;
"""


BODY_CLUSTER = READ + r"""
var W = window; W._vaultAutoIntakeSet(false);
OUT.add = ["The Grandfather", "Gull (dagger)", "Lightsabre"].map(function(n){ return !!(W.vaultHandAdd(n) || {}).ok; });
W.renderVault(); H.flush(60, 3);        /* the card has read the plan; the second copy's task is saved after it */
OUT.add.push(!!(W.vaultHandAdd("The Grandfather") || {}).ok);
W.renderVault(); H.flush(60, 3);
OUT.tasks = tasks(["The Grandfather"]);
OUT.cells = cells(load('uni-weap'));
var w = W._vaultWhereIs("The Grandfather"); OUT.find = w ? (w.cells || []) : null;
"""

BODY_MISFILED = READ + r"""
var W = window; W._vaultAutoIntakeSet(false);
OUT.add = [!!(W.vaultHandAdd("Gull (dagger)") || {}).ok, !!(W.vaultHandAdd("Lightsabre") || {}).ok];
W.renderVault(); H.flush(60, 3);
W.vaultAssign("Lightsabre", "uni-armor");      /* his filing moves it; its saved task still names a UNI-WEAPONS cell */
W.renderVault(); H.flush(60, 3);
OUT.tasks = tasks(["Lightsabre"]);
OUT.armor = cells(load('uni-armor'));
"""


def _fmt(body, **kw):
    return body % dict((k, json.dumps(v)) for k, v in kw.items())


def _by(cells, name):
    return [c["at"] for c in cells if c["n"] == name]


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AMuleCardDrawsACopyWhereItsTaskSendsIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        filed = CLAIM + ("localStorage.setItem('d2r_owned', %s);\nlocalStorage.setItem('d2r_muleAssign', %s);\n"
                         % (json.dumps(json.dumps([FILED])), json.dumps(json.dumps({FILED: "uni-weap"}))))
        cls.w = VPN.run(_fmt(BODY_WEAP, w0=WEAP[0], w1=WEAP[1], w2=WEAP[2], weap=WEAP), prelude=filed, timeout=300)
        base = VPN.run("OUT.r = JSON.parse(window.LSR.getItem('d2r_muleRoster') || 'null') || "
                       "(window._vaultRosterNow && window._vaultRosterNow());", prelude=CLAIM, timeout=300).get("r")
        if not isinstance(base, list) or not base:
            raise AssertionError("PREMISE: the page has no default roster to extend: %r" % (base,))
        roster = [m for m in base if not str(m.get("id", "")).startswith("war-law-")] + [{"id": WAR, "name": "WAR1"}]
        cls.v = VPN.run(_fmt(BODY_WAR, adds=[SHAKO] * 3 + [BELT] * 6, shako=SHAKO, belt=BELT, war=WAR),
                        prelude=CLAIM + "localStorage.setItem('d2r_muleRoster', %s);\n" % json.dumps(json.dumps(roster)), timeout=300)
        pos = {"uni-weap": {"Lightsabre": {"tab": "personal", "page": 0, "x": 1, "y": 0, "at": "2026-10-28T00:00:00Z"}}}
        cls.h = VPN.run(_fmt(BODY_HAND, weap=WEAP),
                        prelude=CLAIM + "localStorage.setItem('d2r_mulePos', %s);\n" % json.dumps(json.dumps(pos)), timeout=300)
        cls.n = VPN.run(BODY_NINE, prelude=CLAIM, timeout=300)
        cls.c = VPN.run(BODY_CLUSTER, prelude=CLAIM, timeout=300)
        # Gull then Lightsabre by hand (tasks UNI-WEAPONS c0r0, c1r0), then he files Lightsabre on UNI-ARMOR: the saved task
        # still names UNI-WEAPONS c1r0, and UNI-ARMOR's card must not draw it there
        cls.m = VPN.run(BODY_MISFILED, prelude=CLAIM, timeout=300)

    def test_the_premise_every_hand_add_has_its_own_task_cell(self):
        for o in (self.w, self.v, self.h, self.n):
            self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
            self.assertTrue(o.get("add") and all(o["add"]), "PREMISE: a hand add did not land: %r" % o.get("add"))
        cells = [t[0]["cell"] for t in self.w["tasks"].values()]
        self.assertTrue(all(cells) and len(set(cells)) == 3, "PREMISE: %r" % self.w["tasks"])
        self.assertNotEqual(self.w["tasks"]["The Grandfather"][0]["cell"], "stash:c0r0",
                            "PREMISE: the biggest item got the first cell, so the old packer would agree by luck: %r" % self.w["tasks"])

    def test_the_card_draws_each_copy_at_its_task_cell(self):
        for n in WEAP:
            self.assertEqual(_by(self.w["cells"], n), [self.w["tasks"][n][0]["cell"]],
                             "%s: the card draws %r, its task says %r" % (n, _by(self.w["cells"], n), self.w["tasks"][n]))

    def test_a_copy_with_no_task_still_packs_and_nothing_overlaps(self):
        self.assertEqual(len(_by(self.w["cells"], FILED)), 1, "the filed item with no task is not drawn: %r" % self.w["cells"])
        self.assertFalse(self.w["fault"]["fault"], "two copies share cells on the card: %r" % self.w["fault"])

    def test_find_names_the_task_cell(self):
        for n in WEAP:
            m = re.match(r"^stash:c(\d+)r(\d+)$", self.w["tasks"][n][0]["cell"])
            want = "Personal stash · col %d · row %d" % (int(m.group(1)) + 1, int(m.group(2)) + 1)
            self.assertEqual(self.w["find"][n], [want], "FIND names %r for %s, its task says %s" % (self.w["find"][n], n, want))

    def test_a_war_mule_draws_its_over_cap_copies_at_their_task_cells(self):
        want = sorted(t["cell"] for n in (SHAKO, BELT) for t in self.v["tasks"][n] if t and t["id"] == WAR)
        self.assertEqual(len(want), 4, "PREMISE: not four copies bound for WAR1: %r" % self.v["tasks"])
        self.assertEqual(sorted(c["at"] for c in self.v["cells"]), want, "WAR1 draws %r, its tasks say %r" % (self.v["cells"], want))

    def test_his_hand_spot_wins_over_a_task_cell(self):
        h = self.h
        self.assertEqual([(c["at"], c["hand"]) for c in h["cells"] if c["n"] == "Lightsabre"], [("stash:c1r0", True)], h["cells"])
        self.assertEqual(_by(h["cells"], "Gull (dagger)"), [h["tasks"]["Gull (dagger)"][0]["cell"]], h)
        self.assertEqual(len(_by(h["cells"], "The Grandfather")), 1, h["cells"])
        self.assertFalse(h["fault"]["fault"], "a task cell was drawn over his hand spot: %r" % h["fault"])
        self.assertEqual(h["conflicts"], 0, "his own spot was reported as not fitting: %r" % h)

    def test_a_second_copy_added_later_is_drawn_beside_its_sibling_where_its_task_says(self):
        """The planner puts a later copy on the free cell nearest its sibling (c0r4 under the first, here); a card that packs
        it first-fit puts it at c5r0. This is the shape that makes the two disagree after the first paint."""
        c = self.c
        self.assertEqual(c["__boot"]["errors"], [], c["__boot"])
        self.assertTrue(c.get("add") and all(c["add"]), "PREMISE: %r" % c.get("add"))
        want = [t["cell"] for t in c["tasks"]["The Grandfather"]]
        self.assertEqual(len(set(want)), 2, "PREMISE: two copies, two task cells: %r" % want)
        got = dict((x["key"], x["at"]) for x in c["cells"] if x["n"] == "The Grandfather")
        self.assertEqual([got.get("The Grandfather"), got.get("The Grandfather #2")], want,
                         "copy 1 / copy 2 are drawn at %r, their tasks say %r" % (got, want))
        m = re.match(r"^stash:c(\d+)r(\d+)$", want[1])
        self.assertIn("Personal stash · col %d · row %d" % (int(m.group(1)) + 1, int(m.group(2)) + 1), c["find"] or [], c["find"])

    def test_a_task_bound_for_another_locker_is_not_drawn_here(self):
        m = self.m
        self.assertEqual(m["__boot"]["errors"], [], m["__boot"])
        t = (m["tasks"]["Lightsabre"] or [None])[0] or {}
        self.assertTrue(m.get("add") and all(m["add"]), "PREMISE: a hand add did not land: %r" % m.get("add"))
        self.assertEqual(t.get("id"), "uni-weap", "PREMISE: the refiled item has no move task to UNI-WEAPONS: %r" % m["tasks"])
        self.assertNotEqual(t.get("cell"), "stash:c0r0", "PREMISE: its task cell is the first cell, so no packer could differ: %r" % t)
        self.assertEqual(_by(m["armor"], "Lightsabre"), ["stash:c0r0"],
                         "UNI-ARMOR draws Lightsabre at %r - its task's cell on another locker" % _by(m["armor"], "Lightsabre"))

    def test_nine_copies_take_their_nine_cells_and_the_mule_still_has_room(self):
        n = self.n
        want = sorted(t["cell"] for t in n["tasks"]["The Grandfather"])
        self.assertEqual(len(set(want)), 9, "PREMISE: nine copies, nine task cells: %r" % want)
        self.assertEqual(sorted(_by(n["cells"], "The Grandfather")), want, "the copies are not drawn at their own cells")
        self.assertIs(n["room"], True, "nine 2x4 on a 140-cell mule leave room for one more; the room probe counted them twice")


RED_PROOF = [
    {"why": "#144.10 (REG-2782) - the card re-packs every copy largest-first again",
     "file": "bible.html",
     "find": "    var _plan = (muleId != null && typeof _vaultPlanOn === 'function') ? _vaultPlanOn(muleId) : null;\n",
     "replace": "    var _plan = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "#144.10 (REG-2782) - every copy of a name is sent to its first task cell",
     "file": "bible.html",
     "find": "if (pl[q].ci === it.ci) { _planAt[it.key] = pl[q]; return; }",
     "replace": "if (pl[q]) { _planAt[it.key] = pl[0]; return; }",
     "matches": 1, "needs": "node"},
    {"why": "#144.10 (REG-2782) - a task cell is drawn over his hand spot",
     "file": "bible.html",
     "find": "          if (pl.x < o.x + o.w && o.x < pl.x + it.w && pl.y < o.y + o.h && o.y < pl.y + it.h) ok = false;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "#144.10 (REG-2782) - the room probe re-packs the task-placed copies on top of themselves",
     "file": "bible.html",
     "find": ".filter(function(x){ return !x.manual && !x.planned; }); /* #144.10 seeded, not re-packed */",
     "replace": ".filter(function(x){ return !x.manual; }); /* #144.10 seeded, not re-packed */",
     "matches": 1, "needs": "node"},
    {"why": "#144.10 (REG-2782) - the plan is read once and never again after the store changes",
     "file": "bible.html",
     "find": "    var bag = (_vaultPlanMemo && _vaultPlanMemo.raw === raw && window._vaultMemoOff !== true) ? _vaultPlanMemo.bag : null;\n",
     "replace": "    var bag = (_vaultPlanMemo && window._vaultMemoOff !== true) ? _vaultPlanMemo.bag : null;\n",
     "matches": 1, "needs": "node"},
    {"why": "#144.10 (REG-2782) - a task bound for another locker is drawn on this one",
     "file": "bible.html",
     "find": "      if (to.id != null ? String(to.id) !== String(muleId) : (mName == null || String(to.holder || '') !== mName)) return;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
