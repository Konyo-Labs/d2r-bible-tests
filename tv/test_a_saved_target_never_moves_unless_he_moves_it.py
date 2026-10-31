# -*- coding: utf-8 -*-
"""REG-2787 (his words 2026-10-28 ~19:05 IDT, #154) - A SAVED MOVE TARGET NEVER MOVES UNLESS HE MOVES IT.

His words: "also obivously needs to remember and always organize the items the same. meaning if i restart my console those
same items need to know where they were told to go and be so they dont mix up between restarts and stuff... needs some
safegaurds maybe here."

MEASURED on the whole page in node before the fix. 21 targets were planned, then put through eight steps: a reload; a new
big item, a new item and a second copy; another task ticked; 495 rings and two more Shakos that fill the war stash's 5 pages
and make the board create WAR1; a reload; a deleted item; WAR1 and UNI-WEAPONS renamed; and a reload. 0 of the 21 saved
targets moved, and 0 of the 521 there by the end moved, with no two targets overlapping. A copy is drawn on the card and named
in FIND at the cell its saved target names. The board already keeps a saved target in three places: the stored move is
returned as saved, the packer takes its cell before it places anything new, and a rebuild of the records carries every saved
move forward.

Three changes that had to move a target did not:
- An item the rules place elsewhere (Carrion Wind) that he files by hand on UNI-ARMOR. Its task still sent it to SHARED STASH
  (1,1), while its card and FIND drew it on UNI-ARMOR.
- Lightsabre, which he placed by hand at col 7 · row 6 on its card. Its task still said stash:c0r0.
- WAR1 after he took it back (deleted and declined). Two Shako rows still said "-> WAR1 (1,1)" / "(3,1)", a mule that no
  longer exists, and gave no reason.

Now his hand re-targets: a re-file that changes where the item lives, and a spot on page 1 of a mule card. A target on a
deleted mule is the one target the board plans again by itself. Each of these sets the task back to to-move, and its row
says why ("new target: ..."). A re-file the L1 rules overrule leaves the target where it is, at the rules' home. So does a
re-file of war gear onto a WAR mule. A mule store that will not read is UNKNOWN, never "deleted", so the saved targets stay.

Driven on the whole page in node (vault_page_node), never a browser on his Mac. RED_PROOF below.
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
SHAKO = "Harlequin Crest (Shako)"
SOJ = "The Stone of Jordan"

LIB = r"""
var W = window;
function snap(){
  var rec = JSON.parse(W.LSR.getItem('d2r_vaultRecords') || '{}'), out = {};
  (rec.records || []).forEach(function(r){
    if (!r || !r.move || !r.move.to || r.move.kind === 'throw') return;
    var t = r.move.to, c = null;
    try { c = _itemCells(r.name); } catch (e) {}
    out[r.name + '#' + (r.copyIx || 0)] = { id: t.id == null ? null : t.id, cell: t.cell || null,
      status: r.move.status || null, re: r.move.retarget ? r.move.retarget.why : null, w: c ? c.w || 1 : 1, h: c ? c.h || 1 : 2 };
  });
  return out;
}
function drawn(names){ var o = {}; names.forEach(function(n){ var w = null; try { w = W._vaultWhereIs(n); } catch (e) {}
  o[n] = w ? (w.cells || []).map(function(c){ return String(c).replace(/^[^·]*WAR1 · |^DEANSORC · /, 'WAR · '); }) : null; }); return o; }
function paint(){ W.renderVault(); H.flush(60, 3); }
function add(n, k){ for (var i = 0; i < (k || 1); i++) W.vaultHandAdd(n); }
function task(n, i){ var x = (W._vaultMoveEnsure(n, i || 0) || {}).task; return x ? { id: (x.to && x.to.id != null) ? x.to.id : null, cell: (x.to && x.to.cell) || null, status: x.status, re: x.retarget ? x.retarget.why : null } : null; }
function list(){ return (document.getElementById('vault-move-list') || {}).innerHTML || ''; }
function rows(n){ return (list().match(/<li class="vmv-row[^>]*>[\s\S]*?<\/li>/g) || []).filter(function(r){ return r.indexOf('data-name="' + n + '"') >= 0; })
  .map(function(r){ return { chip: ((r.match(/<b class="vmv-l1 vmv-retarget" data-retarget="1" title="([^"]*)"/) || [])[1]) || null,
                             to: ((r.match(/<span class="vtk-to">([^<]*)/) || [])[1]) || null }; }); }
function warId(){ var w = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return m.role === 'war'; })[0]; return w ? w.id : null; }
function carry(){ var o = {}; H.RAW.forEach(function(v, k){ o[k] = v; }); return o; }
"""

MULE = ["Gull", "The Grandfather", "Lightsabre", "Arkaine's Valor", "Andariel's Visage", "Gheed's Fortune",
        "Tal Rasha's Guardianship"]
WAR0 = [SHAKO, "Griffon's Eye", "Annihilus", "Mara's Kaleidoscope", SOJ]

CHAIN = [
    ("plan", "W._vaultAutoIntakeSet(false);" + "".join("add(%s);" % json.dumps(n) for n in MULE + WAR0)
             + "add(%s, 9); paint();" % json.dumps(SOJ)),
    ("a reload", "paint();"),
    ("a new big item, a new item and a second copy", "W._vaultAutoIntakeSet(false); add('Windforce'); add('Death\\'s Fathom'); add('Gull'); paint();"),
    ("another item's task ticked", "W._vaultMoveMark('Lightsabre', 0); paint();"),
    ("the war stash filled and WAR1 made", "W._vaultAutoIntakeSet(false); add(%s, 495); add(%s, 2); paint(); OUT.war = warId();"
                                           % (json.dumps(SOJ), json.dumps(SHAKO))),
    ("a reload", "paint();"),
    ("an item deleted", "OUT.rm = (W.vaultRemove(['The Grandfather'], { lane: 'law', quiet: true, exact: true, why: 'law' }) || {}).removed; paint();"),
    ("mules renamed", "W.prompt = function(){ return 'DEANSORC'; }; W.vaultRenameMule(warId());"
                      "W.prompt = function(){ return 'MY WEAPS'; }; W.vaultRenameMule('uni-weap'); paint();"),
    ("a reload", "paint();"),
]


def _prelude(raw):
    return "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(v)) for k, v in raw.items())


def _step(prelude, body):
    r = VPN.run(LIB + body + "\nOUT.snap = snap(); OUT.html = list(); OUT.raw = carry();", prelude=prelude, timeout=600)
    return r


def _overlaps(s):
    by, hits = {}, []
    for k, v in s.items():
        m = re.match(r"^(\w+):c(\d+)r(\d+)$", v["cell"] or "")
        if m:
            by.setdefault((v["id"], m.group(1)), []).append((k, int(m.group(2)), int(m.group(3)), v["w"], v["h"]))
    for L in by.values():
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                a, b = L[i], L[j]
                if a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
                    hits.append((a[0], b[0]))
    return hits


BODY_REFILE = LIB + r"""
var CW = 'Carrion Wind';
W._vaultAutoIntakeSet(false);
[CW, 'Gull', 'Lightsabre', %(shako)s, %(shako)s, %(shako)s].forEach(function(n){ add(n); }); paint();
OUT.before = { cw: task(CW), gull: task('Gull (dagger)'), light: task('Lightsabre'), shako: [1, 2].map(function(i){ return task(%(shako)s, i); }) };
W.vaultAssign(CW, 'uni-armor'); paint();
OUT.cw1 = task(CW); OUT.cwRows1 = rows(CW); OUT.cwDrawn1 = (W._vaultWhereIs(CW) || {}).cells || null;
W._vaultMoveMark(CW, 0);
OUT.cwTicked = task(CW).status;
W.vaultAssign(CW, 'uni-weap'); paint();
OUT.cw2 = task(CW);
W.vaultAssign('Gull (dagger)', 'uni-armor'); paint();
OUT.gull = task('Gull (dagger)'); OUT.gullRows = rows('Gull (dagger)');
var war = warId(); OUT.war = war;
if (war) W.vaultAssign(%(shako)s, war); paint();
OUT.shako = [1, 2].map(function(i){ return task(%(shako)s, i); });
OUT.light = task('Lightsabre');
""" % {"shako": json.dumps(SHAKO)}

BODY_SPOT = LIB + r"""
W._vaultAutoIntakeSet(false);
['Lightsabre', 'Gull', 'The Grandfather'].forEach(function(n){ add(n); }); paint();
OUT.before = { light: task('Lightsabre'), gull: task('Gull (dagger)'), gf: task('The Grandfather') };
OUT.place = W._mpPlace('uni-weap', 'Lightsabre', { tab: 'personal', page: 0, x: 6, y: 5 }); paint();
OUT.light = task('Lightsabre'); OUT.lightRows = rows('Lightsabre'); OUT.drawn = (W._vaultWhereIs('Lightsabre') || {}).cells || null;
OUT.gull = task('Gull (dagger)'); OUT.gf = task('The Grandfather');
OUT.raw = carry();
"""

BODY_SPOT_RELOAD = LIB + r"""
paint();
OUT.light = task('Lightsabre'); OUT.drawn = (W._vaultWhereIs('Lightsabre') || {}).cells || null;
"""

BODY_WAR = LIB + r"""
W._vaultAutoIntakeSet(false);
[%(shako)s, %(shako)s, %(shako)s].forEach(function(n){ add(n); }); paint();
OUT.war = warId();
OUT.before = [0, 1, 2].map(function(i){ return task(%(shako)s, i); });
OUT.raw = carry();
""" % {"shako": json.dumps(SHAKO)}

BODY_AFTER = LIB + r"""
paint();
try { OUT.roster = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').map(function(m){ return m.id; }); } catch (e) { OUT.roster = null; }
OUT.after = [0, 1, 2].map(function(i){ return task(%(shako)s, i); });
OUT.rows = rows(%(shako)s);
""" % {"shako": json.dumps(SHAKO)}


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ASavedTargetNeverMovesUnlessHeMovesIt(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.chain, pre = [], CLAIM
        for label, body in CHAIN:
            r = _step(pre, body)
            pre = _prelude(r.pop("raw"))
            cls.chain.append((label, r))
        cls.refile = VPN.run(BODY_REFILE, prelude=CLAIM, timeout=300)
        cls.spot = VPN.run(BODY_SPOT, prelude=CLAIM, timeout=300)
        cls.spotReload = VPN.run(BODY_SPOT_RELOAD, prelude=_prelude(cls.spot.pop("raw")), timeout=300)
        w = VPN.run(BODY_WAR, prelude=CLAIM, timeout=300)
        cls.war, raw = w, w.pop("raw")
        R = json.loads(raw["d2r_muleRoster"])
        gone = [m for m in R if m.get("id") != w["war"]]
        for m in gone:
            if m.get("id") == "shared":
                m["warDeclined"] = ["WAR1"]      # what his delete door records (REG-2803) before it removes the mule
        took = dict(raw, d2r_muleRoster=json.dumps(gone))
        cls.deleted = VPN.run(BODY_AFTER, prelude=_prelude(took), timeout=300)
        cls.held = VPN.run(BODY_AFTER, prelude=_prelude(dict(raw, d2r_muleRoster="{not a roster")), timeout=300)

    def test_no_saved_target_moves_through_restarts_arrivals_the_war_replan_a_delete_or_a_rename(self):
        prev = None
        for label, r in self.chain:
            self.assertEqual(r["__boot"]["errors"], [], (label, r["__boot"]))
            s = r["snap"]
            self.assertEqual(_overlaps(s), [], "two saved targets overlap after %s" % label)
            self.assertNotIn('data-retarget="1"', r["html"], "a row says its target changed after %s, which no hand did" % label)
            if prev is not None:
                moved = [(k, (v["id"], v["cell"]), (s[k]["id"], s[k]["cell"])) for k, v in prev.items()
                         if k in s and (v["id"], v["cell"]) != (s[k]["id"], s[k]["cell"])]
                self.assertEqual(moved, [], "saved targets moved on %s: %r" % (label, moved[:6]))
                lost = [k for k in prev if k not in s and not k.startswith("The Grandfather#")]
                self.assertEqual(lost, [], "saved targets vanished on %s: %r" % (label, lost[:6]))
            prev = s
        first, last = self.chain[0][1]["snap"], self.chain[-1][1]["snap"]
        self.assertEqual(len(first), 21, "PREMISE: the plan did not give all 21 copies a target: %d" % len(first))
        self.assertTrue(all(v["cell"] for v in first.values()), "PREMISE: a planned copy has no cell")
        self.assertGreater(len(last), 500, "PREMISE: the war fill did not arrive: %d targets" % len(last))
        war = self.chain[4][1].get("war")
        self.assertTrue(war, "PREMISE: the war fill did not make the board create WAR1")
        self.assertTrue(any(v["id"] == war for v in last.values()), "PREMISE: nothing targets the WAR1 the board made")
        self.assertEqual(self.chain[6][1].get("rm"), ["The Grandfather"], "PREMISE: the delete did not land")

    def test_his_refile_retargets_the_copy_and_the_row_says_why(self):
        r = self.refile
        self.assertEqual(r["__boot"]["errors"], [], r["__boot"])
        # v3849 B9: a hand-added trash unique files by its kind (Carrion Wind -> UNI-SMALL), no longer SHARED STASH. The
        # premise this law needs is only that the rules first planned it on a locker OTHER than the one he files it on.
        self.assertTrue(r["before"]["cw"]["id"] and r["before"]["cw"]["cell"], "PREMISE: Carrion Wind was not planned: %r" % r["before"])
        self.assertNotIn(r["before"]["cw"]["id"], ("uni-armor", "uni-weap"),
                         "PREMISE: Carrion Wind was first planned where he files it: %r" % r["before"])
        c1 = r["cw1"]
        self.assertEqual(c1["id"], "uni-armor", "his re-file left the task on another locker: %r" % c1)
        self.assertTrue(c1["cell"], c1)
        self.assertEqual(c1["re"], "you filed it on UNI-ARMOR", c1)
        self.assertEqual([x["chip"] for x in r["cwRows1"]], ["you filed it on UNI-ARMOR"], "the row does not say why: %r" % r["cwRows1"])
        m = re.match(r"^stash:c(\d+)r(\d+)$", c1["cell"])
        self.assertIn("Personal stash · col %d · row %d" % (int(m.group(1)) + 1, int(m.group(2)) + 1), r["cwDrawn1"] or [],
                      "the card draws it away from its new task cell: %r / %r" % (c1, r["cwDrawn1"]))
        self.assertEqual(r["cwTicked"], "moved-manual", "PREMISE: the tick did not land")
        self.assertEqual((r["cw2"]["id"], r["cw2"]["status"]), ("uni-weap", "to-move"),
                         "a re-file after a tick kept the old tick on a new target: %r" % r["cw2"])

    def test_a_refile_the_rules_overrule_and_war_gear_on_a_war_mule_keep_their_target(self):
        r = self.refile
        self.assertEqual(r["gull"]["id"], r["before"]["gull"]["id"], "L1: Gull's target left the rules' home: %r" % r["gull"])
        self.assertEqual(r["gull"]["cell"], r["before"]["gull"]["cell"], r["gull"])
        self.assertEqual([x["chip"] for x in r["gullRows"]], [None] * len(r["gullRows"]), r["gullRows"])
        self.assertTrue(r["war"], "PREMISE: no WAR1 to file the Shako on")
        self.assertEqual(r["shako"], r["before"]["shako"], "filing war gear on its WAR mule moved its targets: %r / %r" % (r["before"]["shako"], r["shako"]))
        self.assertEqual(r["light"], r["before"]["light"], "a re-file of other items moved Lightsabre's target: %r" % r["light"])

    def test_his_hand_spot_on_a_card_is_the_copys_target(self):
        r = self.spot
        self.assertEqual(r["__boot"]["errors"], [], r["__boot"])
        self.assertTrue((r["place"] or {}).get("ok"), "PREMISE: the spot was refused: %r" % r["place"])
        self.assertNotEqual(r["before"]["light"]["cell"], "stash:c6r5", "PREMISE: Lightsabre was already planned there")
        self.assertEqual((r["light"]["id"], r["light"]["cell"]), ("uni-weap", "stash:c6r5"), "his spot did not become the target: %r" % r["light"])
        self.assertIn("Personal stash · col 7 · row 6", r["drawn"] or [], r["drawn"])
        self.assertEqual([x["chip"] for x in r["lightRows"]], ["you placed it at col 7 · row 6 by hand"], r["lightRows"])
        self.assertEqual((r["gull"], r["gf"]), (r["before"]["gull"], r["before"]["gf"]), "his spot moved other targets")
        self.assertEqual(self.spotReload["light"]["cell"], "stash:c6r5", "a reload lost his spot's target: %r" % self.spotReload["light"])

    def test_a_target_on_a_deleted_mule_plans_again_and_says_why(self):
        w, d = self.war, self.deleted
        self.assertTrue(w["war"], "PREMISE: the board made no WAR1")
        self.assertEqual([t["id"] for t in w["before"]], ["shared", w["war"], w["war"]], "PREMISE: %r" % w["before"])
        self.assertNotIn(w["war"], d["roster"], "PREMISE: WAR1 is still on the roster")
        self.assertEqual(d["after"][0], w["before"][0], "the keeper in the war stash moved: %r" % d["after"][0])
        for t in d["after"][1:]:
            self.assertNotEqual(t["id"], w["war"], "a task still sends a copy to the deleted WAR1: %r" % d["after"])
            self.assertEqual(t["re"], "WAR1 was deleted", t)
        chips = [x["chip"] for x in d["rows"]]
        self.assertEqual(chips.count("WAR1 was deleted"), len(d["rows"]) - 1,
                         "the rows of the copies WAR1 held do not say why: %r" % d["rows"])
        self.assertFalse(any((x["to"] or "").startswith("WAR1") for x in d["rows"]), "a row still says -> WAR1: %r" % d["rows"])

    def test_a_mule_store_that_will_not_read_keeps_every_saved_target(self):
        w, h = self.war, self.held
        self.assertEqual(h["after"], w["before"], "a held mule store re-planned saved targets: %r" % h["after"])
        self.assertFalse(any(x["chip"] for x in h["rows"]), h["rows"])


RED_PROOF = [
    {"why": "REG-2787 - a restart forgets the saved targets (the bag reads no saved move), so arrivals re-pack them",
     "file": "bible.html",
     "find": "        map[String(r.name) + '\\u0000' + (r.copyIx || 0)] = r.move;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - a rebuild of the records (a new name arriving) drops the saved targets it carries",
     "file": "bible.html",
     "find": "        priorMove[String(r.name) + '\\u0000' + (r.copyIx || 0)] = r.move;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - his re-file does not re-target (the task keeps sending it to another locker)",
     "file": "bible.html",
     "find": "      if (r && r.ok && witness && witness.by === 'hand') {",
     "replace": "      if (false) {",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - a re-file re-targets copies already on the locker the rules give them",
     "file": "bible.html",
     "find": "      if (st.to.id != null ? String(st.to.id) === String(h.id) : String(st.to.holder || '') === String(h.holder || '')) continue;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - filing war gear on a WAR mule re-targets its over-cap copies",
     "file": "bible.html",
     "find": "      if (h.id === 'shared' && tm && _vaultWarRole(tm)) continue;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - a re-target keeps the old tick, so the new target reads as already moved",
     "file": "bible.html",
     "find": "        status: 'to-move', evidence: [], manual: st.manual, retarget: { why: why, at: at } } });",
     "replace": "        status: st.status, evidence: [], manual: st.manual, retarget: { why: why, at: at } } });",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - his hand spot on a card does not become the copy's target",
     "file": "bible.html",
     "find": "    if (pg === 0 && (spot.tab === 'personal' || spot.tab === 'inv') && typeof window._vaultMoveRetargetCell === 'function') {",
     "replace": "    if (false) {",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - a task keeps sending a copy to a deleted mule",
     "file": "bible.html",
     "find": "        && typeof muleById === 'function' && !muleById(stored.to.id)\n",
     "replace": "        && false\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - a mule store that will not read re-plans every target on an added mule as deleted",
     "file": "bible.html",
     "find": "        && !(typeof window._vaultHeldFor === 'function' && window._vaultHeldFor(['d2r_muleRoster']))) {",
     "replace": "        ) {",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - a re-planned copy forgets why (the fresh plan drops the note)",
     "file": "bible.html",
     "find": "      retarget: _rt,   /* REG-2787 why this copy planned again */\n",
     "replace": "      retarget: null,\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - the task's sanitizer drops why the target changed",
     "file": "bible.html",
     "find": "      out.retarget = { why: spec.retarget.why, at: (typeof spec.retarget.at === 'string') ? spec.retarget.at : null };\n",
     "replace": "      out.retargetX = 1;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2787 - the row does not say why its target changed",
     "file": "bible.html",
     "find": "        + ((!thr && t.retarget) ? '<b class=\"vmv-l1 vmv-retarget\"",
     "replace": "        + ((false && t.retarget) ? '<b class=\"vmv-l1 vmv-retarget\"",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
