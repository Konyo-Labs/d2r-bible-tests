# -*- coding: utf-8 -*-
"""REG-2803 (his ruling 2026-10-28 ~17:50 IDT) - THE BOARD MAKES THE WAR MULE THE OVERFLOW NEEDS, AND TASKS HIM TO MAKE IT IN
THE GAME.

His words: "yea the board should automatically create a mule and name it War1/War2 for each mule and prompt me to create
that same mule ingame so i get tasked to do it". It supersedes L1's line of 2026-10-20, "a mule is never created".
MEASURED before (node, whole page): Shako x3 hand-added with no WAR mule - the war cap keeps 1, and the 2 extra copies kept
NO cell; MOVE TASKS said "make a mule named WAR1" and nothing else happened.

Now the move paint makes WAR1 (then WAR2 ...) under the add-mule door's rules - added:true (his delete takes it back), the
war role on its id, and a record of who made it, when and why - plans again so the copies land on it, and puts "Create
mule WAR1 in the game" first in MOVE TASKS until he ticks it or the reader sees an item on a character of that name. Each
guard is a case here: one WAR1 across repeated paints and a reload; nothing made without a real overflow; nothing in a
shadow, a guest's world, or while the mule store is UNKNOWN; nothing from FIND, the copy readout or a row's expand; and a
WAR mule he deleted is not made again (REG-2997: the next one is).

Driven on the whole page in node (vault_page_node - never a browser on his Mac). RED_PROOF below.
"""
import io
import json
import os
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
SHAKO = "Harlequin Crest (Shako)"      # big war gear: the war cap keeps 1, every other copy needs a WAR mule
SEEDED = ("localStorage.setItem('d2r_owned', %s);\nlocalStorage.setItem('d2r_copies', %s);\n"
          % (json.dumps(json.dumps([SHAKO])), json.dumps(json.dumps({SHAKO: 3}))))
# a law-only switch: the paint's make is suspended, so the read-only doors can be asked on a real overflow first
NO_PAINT_MAKE = ("  function _vaultWarAutoMule(){\n    var made = [];\n",
                 "  function _vaultWarAutoMule(){\n    var made = [];\n    if (window.__lawNoPaintMake) return { made: made, why: 'law' };\n", 1)

READ = r"""
var W = window, SH = %(shako)s;
function wars(){ return JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return /^war/i.test(String(m.name || '')); }); }
function list(){ return (document.getElementById('vault-move-list') || {}).innerHTML || ''; }
/* REG-2888 - the WAR mule's make rows only: since REG-2895 the board also makes the dedicated CHARMS mule and asks him to make
   it in the game, and this law is about the WAR mule's row (measured on int-7: 2 make rows, CHARMS and WAR1) */
function makeRows(){ return (list().match(/<li class="vtk-line vtk-make"[\s\S]*?<\/li>/g) || []).map(function(x){ return x.replace(/<[^>]+>/g, ''); })
  .filter(function(t){ return t.indexOf('Create mule ' + W._vaultWarName(1) + ' ') >= 0 || t.indexOf('Create mule ' + W._vaultWarName(2) + ' ') >= 0; }); }   /* REG-2980 the war mule's letter name */
OUT.w1 = W._vaultWarName(1);
function tasks(){ var o = []; for (var ci = 0; ci < copyCount(SH); ci++) { var t = (W._vaultMoveEnsure(SH, ci) || {}).task; o.push(t && t.to ? [t.to.holder || null, t.to.cell || null] : null); } return o; }
""" % {"shako": json.dumps(SHAKO)}

BODY_MADE = READ + r"""
W._vaultAutoIntakeSet(false);
OUT.add = [SH, SH, SH].map(function(n){ return !!(W.vaultHandAdd(n) || {}).ok; });
W.renderVault(); H.flush(60, 3); W.renderVault(); W.renderVault();
OUT.wars = wars(); OUT.tasks = tasks(); OUT.make = makeRows();
OUT.makeFirst = list().indexOf('data-sec="make"') >= 0 && list().indexOf('data-sec="make"') < list().indexOf('data-sec="moves"');
/* REG-2888 - the WAR1 card's own badge: the CHARMS mule the board makes (REG-2895) wears the same badge on its own card */
function warBadge(){ var h = (document.getElementById('vault-shelf') || {}).innerHTML || '', w = wars()[0], at = w ? h.indexOf('data-vault-mule="' + w.id + '"') : -1;
  if (at < 0) return null; var nx = h.indexOf('data-vault-mule="', at + 10); return h.slice(at, nx < 0 ? h.length : nx).indexOf('class="nig-chip"') >= 0; }
OUT.badge = warBadge();
/* the card's delete button is drawn only for a mule his delete door takes (_vmAddedMule) - ask the page, not a copy of its rule */
OUT.deletable = OUT.wars.length ? (((document.getElementById('vault-shelf') || {}).innerHTML || '').indexOf("window.vaultDeleteMule('" + OUT.wars[0].id + "')") >= 0) : null;
OUT.raw = {}; H.RAW.forEach(function(v, k){ OUT.raw[k] = v; });
var id = OUT.wars.length ? OUT.wars[0].id : null;
OUT.tick = id ? W._vaultWarMadeInGame(id) : null;
OUT.afterTick = { wars: wars(), make: makeRows(), badge: warBadge() };
OUT.declineWar = id ? W._vaultWarDecline(wars()[0]) : null;   /* the stored WAR1: the role is what decides */
"""

BODY_RELOAD = READ + r"""
W.renderVault(); H.flush(60, 3); W.renderVault();
OUT.wars = wars(); OUT.tasks = tasks();
"""

BODY_NONE = READ + r"""
W._vaultAutoIntakeSet(false);
OUT.add = [SH, 'The Stone of Jordan', 'The Stone of Jordan', 'Raven Frost'].map(function(n){ return !!(W.vaultHandAdd(n) || {}).ok; });
W.renderVault(); H.flush(60, 3);
OUT.wars = wars(); OUT.full = (W._vaultWarFull || []).length;
"""

BODY_SEEN = READ + r"""
W._vaultAutoIntakeSet(false);
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); });
W.renderVault(); H.flush(60, 3);
OUT.before = makeRows();
W._ownedProvWrite(SH, { source: 'intake-read', by: 'law', holder: W._vaultWarName(1), loc: 'stash', cell: 'stash:c0r0', sessionId: 's-war1', frameId: 'f-war1', ts: Date.now() });
W.renderVault(); H.flush(60, 3);
OUT.after = makeRows(); OUT.wars = wars();
"""

BODY_GUEST = READ + r"""
OUT.owner = W._D2R_OWNER;
W._vaultAutoIntakeSet(false);
OUT.add = [SH, SH, SH].map(function(n){ return !!(W.vaultHandAdd(n) || {}).ok; });
W.renderVault(); H.flush(60, 3);
OUT.wars = wars(); OUT.auto = W._vaultWarAuto || null;
OUT.anyWar = []; H.RAW.forEach(function(v, k){ if (/muleRoster/.test(k) && /"name":"WAR/i.test(v)) OUT.anyWar.push(k); });
"""

BODY_HELD = READ + r"""
W.renderVault(); H.flush(60, 3);
OUT.auto = W._vaultWarAuto || null;
try { W._vaultMoveEnsure(SH, 1); } catch (e) {}   /* the plan for an extra copy (fresh, unsaved): it fills _vaultWarFull */
OUT.full = (W._vaultWarFull || []).length;
OUT.bytes = H.RAW.get('d2r_muleRoster');
"""

BODY_READONLY = READ + r"""
W.renderVault(); H.flush(60, 3);
OUT.premise = wars().length;
try { W.vaultFind('shako'); H.flush(400, 3); } catch (e) { OUT.findErr = String(e && e.message || e); }
OUT.where = (W._vaultWhereIs(SH) || {}).cells || null;
try { W._vaultCopyAudit(); } catch (e) { OUT.auditErr = String(e && e.message || e); }
try { W._vaultTaskExpandHtml(SH, 1); W._vaultTaskExpandHtml(SH, 2); } catch (e) { OUT.expandErr = String(e && e.message || e); }
OUT.full = (W._vaultWarFull || []).length;
OUT.afterReadouts = wars().length;
window.__lawNoPaintMake = false;
W._tvdShadow = true; W.renderVault(); H.flush(60, 3);
OUT.inShadow = wars().length; OUT.shadowWhy = (W._vaultWarAuto || {}).why || null;
W._tvdShadow = false; W.renderVault(); H.flush(60, 3);
OUT.afterPaint = wars().map(function(m){ return m.name; });
"""

BODY_DECLINED = READ + r"""
W.renderVault(); H.flush(60, 3); W.renderVault();
OUT.wars = wars(); OUT.w2 = W._vaultWarName(2); OUT.make = makeRows();
OUT.roles = OUT.wars.map(function(m){ return W._vaultWarRole(m); });
"""


def _base_roster():
    r = VPN.run("OUT.r = JSON.parse(window.LSR.getItem('d2r_muleRoster') || 'null') || "
                "(window._vaultRosterNow && window._vaultRosterNow());", prelude=CLAIM, timeout=300).get("r")
    if not isinstance(r, list) or not r:
        raise AssertionError("PREMISE: the page has no default roster: %r" % (r,))
    return [m for m in r if not str(m.get("name", "")).upper().startswith("WAR")]


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheBoardMakesTheWarMuleTheOverflowNeeds(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.made = VPN.run(BODY_MADE, prelude=CLAIM, timeout=300)
        raw = cls.made.pop("raw")
        carry = "".join("localStorage.setItem(%s, %s);\n" % (json.dumps(k), json.dumps(v)) for k, v in raw.items())
        cls.reload = VPN.run(BODY_RELOAD, prelude=carry, timeout=300)
        cls.none = VPN.run(BODY_NONE, prelude=CLAIM, timeout=300)
        cls.seen = VPN.run(BODY_SEEN, prelude=CLAIM, timeout=300)
        cls.guest = VPN.run(BODY_GUEST, prelude="", timeout=300)
        cls.held = VPN.run(BODY_HELD, prelude=CLAIM + SEEDED + "localStorage.setItem('d2r_muleRoster', '{not a roster');\n", timeout=300)
        cls.readonly = VPN.run(BODY_READONLY, prelude=CLAIM + SEEDED + "window.__lawNoPaintMake = true;\n", patches=[NO_PAINT_MAKE], timeout=300)
        roster = _base_roster()
        for m in roster:
            if m.get("id") == "shared":
                m["warDeclined"] = ["WAR1"]
        cls.declined = VPN.run(BODY_DECLINED, prelude=CLAIM + SEEDED + "localStorage.setItem('d2r_muleRoster', %s);\n"
                               % json.dumps(json.dumps(roster)), timeout=300)

    def test_the_board_makes_war1_and_the_extra_copies_land_on_it(self):
        o = self.made
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertEqual(o["add"], [True, True, True], "PREMISE: a hand add did not land: %r" % o["add"])
        self.assertEqual([m["name"] for m in o["wars"]], [o["w1"]], "the board did not make exactly one war mule 1: %r" % o["wars"])
        w = o["wars"][0]
        self.assertEqual((w.get("role"), w.get("warN")), ("war", 1), "WAR1 does not carry the war role on its id: %r" % w)
        self.assertEqual((w.get("auto") or {}).get("by"), "board", "the make is not recorded: %r" % w)
        self.assertTrue((w.get("auto") or {}).get("at") and (w.get("auto") or {}).get("why"), w)
        self.assertTrue(o["deletable"], "the board's WAR1 is not a mule his delete can take back: %r" % w)
        self.assertEqual(o["tasks"][0][0], "SHARED STASH", o["tasks"])
        self.assertEqual([t[0] for t in o["tasks"][1:]], [o["w1"], o["w1"]], "the extra copies did not land on war mule 1: %r" % o["tasks"])
        self.assertTrue(all(t[1] for t in o["tasks"]), "a copy kept no cell: %r" % o["tasks"])

    def test_he_is_tasked_first_to_make_it_in_the_game_until_he_ticks_it(self):
        o = self.made
        self.assertEqual(len(o["make"]), 1, "no single 'make it in the game' task: %r" % o["make"])
        self.assertIn("Create mule %s in the game" % o["w1"], o["make"][0])
        self.assertTrue(o["makeFirst"], "the make task is not above the moves that go to WAR1")
        self.assertTrue(o["badge"], "the WAR1 card does not say the board made it and the game has not seen it yet")
        self.assertEqual(o["tick"], {"ok": True}, o["tick"])
        a = o["afterTick"]
        self.assertEqual((a["wars"][0].get("inGame") or {}).get("by"), "hand", "his tick was not recorded: %r" % a["wars"])
        self.assertEqual((a["make"], a["badge"]), ([], False), "the task or the badge outlived his tick: %r" % a)

    def test_one_war1_across_paints_and_a_reload(self):
        r = self.reload
        self.assertEqual(r["__boot"]["errors"], [], r["__boot"])
        self.assertEqual([m["name"] for m in r["wars"]], [r["w1"]], "a reload made another WAR mule: %r" % r["wars"])
        self.assertEqual([t[0] for t in r["tasks"][1:]], [r["w1"], r["w1"]], r["tasks"])

    def test_no_overflow_makes_no_mule(self):
        n = self.none
        self.assertTrue(all(n["add"]), n["add"])
        self.assertEqual(n["full"], 0, "PREMISE: this vault overflows: %r" % n)
        self.assertEqual(n["wars"], [], "a WAR mule was made with nothing past the war stash: %r" % n["wars"])

    def test_an_item_read_on_war1_closes_the_task_without_a_tick(self):
        s = self.seen
        self.assertEqual(len(s["before"]), 1, "PREMISE: no make task before the read: %r" % s)
        self.assertEqual(s["after"], [], "an item read on a character named WAR1 did not close the task: %r" % s)
        self.assertFalse(s["wars"][0].get("inGame"), "the read was written as his tick: %r" % s["wars"])

    def test_a_guest_world_makes_no_mule(self):
        g = self.guest
        self.assertFalse(g["owner"], "PREMISE: this world is not a guest's: %r" % g)
        self.assertTrue(all(g["add"]), "PREMISE: a guest's hand add did not land: %r" % g)
        self.assertEqual((g["wars"], g["anyWar"]), ([], []), "a guest's world made a WAR mule: %r" % g)
        self.assertIn("guest", (g["auto"] or {}).get("why") or "", g["auto"])

    def test_an_unknown_mule_store_is_never_written(self):
        h = self.held
        self.assertGreater(h["full"], 0, "PREMISE: this vault does not overflow: %r" % h)
        self.assertEqual(h["bytes"], "{not a roster", "the mule store it could not read was written: %r" % h["bytes"])
        self.assertIn("held", (h["auto"] or {}).get("why") or "", "the make did not stop at the held store: %r" % h["auto"])

    def test_find_the_readout_the_expand_and_a_shadow_make_nothing(self):
        r = self.readonly
        self.assertEqual(r["__boot"]["errors"], [], r["__boot"])
        self.assertFalse(r.get("findErr") or r.get("auditErr") or r.get("expandErr"), r)
        self.assertGreater(r["full"], 0, "PREMISE: the readouts were asked on a vault with no overflow: %r" % r)
        self.assertEqual((r["premise"], r["afterReadouts"]), (0, 0), "FIND, the copy readout or the expand made a WAR mule: %r" % r)
        self.assertEqual(r["inShadow"], 0, "a shadow made a WAR mule: %r" % r)
        self.assertEqual(r["afterPaint"], [r["w1"]], "the control: the paint did not make war mule 1 on the same overflow: %r" % r)

    def test_a_war_mule_he_took_back_is_not_made_again(self):
        """REG-2997 (his ruling 2026-10-29, Q2): the number he took back is never made again - the board offers the next one"""
        d = self.declined
        self.assertNotIn(1, d["roles"], "the board made the war mule 1 he deleted again: %r" % d["wars"])
        self.assertEqual([m["name"] for m in d["wars"]], [d["w2"]], "the board did not offer the next war mule: %r" % d["wars"])
        self.assertTrue(any(("Create mule %s " % d["w2"]) in t for t in d["make"]), "he is not tasked to make it: %r" % d["make"])
        self.assertTrue(self.made["declineWar"], "deleting a WAR mule records nothing")

    def test_his_delete_door_records_the_take_back_before_it_removes_the_mule(self):
        src = io.open(os.path.join(os.path.dirname(HERE), "bible.html"), encoding="utf-8").read()
        i = src.index("  window.vaultDeleteMule = async function(id){\n")
        body = src[i:src.index("\n  };\n", i)]
        a = body.find("    try { _vaultWarDecline(m); } catch (eDl) {}\n")
        b = body.find("    roster=roster.filter(function(x){return x.id!==id;});")
        self.assertTrue(0 <= a < b, "the delete door does not record a WAR mule's take-back before it removes it")


RED_PROOF = [
    {"why": "REG-2803 - the move paint never makes the WAR mule (L1's 'a mule is never created' again)",
     "file": "bible.html",
     "find": "      try { _wa = (typeof _vaultWarAutoMule === 'function') ? _vaultWarAutoMule() : null; } catch (eWa) {",
     "replace": "      try { _wa = { made: [], why: 'never' }; } catch (eWa) {",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - the make does not stop when nothing is left over (a mule per paint)",
     "file": "bible.html",
     "find": "      if (!lost) break;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - a mule is made with no overflow at all",
     "file": "bible.html",
     "find": "      var lost = (window._vaultWarFull || []).length;\n",
     "replace": "      var lost = 1;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - a shadow makes a mule",
     "file": "bible.html",
     "find": "    if (window._tvdShadow) return { made: made, why: 'a shadow is read only' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - a guest's world makes a mule",
     "file": "bible.html",
     "find": "    if (window._D2R_OWNER !== true) return { made: made, why: 'a guest world makes no mule' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - the make does not stop at a held mule store",
     "file": "bible.html",
     "find": "    var held = (typeof window._vaultHeldFor === 'function') ? window._vaultHeldFor([RK]) : null;\n    if (held) return { made: made, why: held.why };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - a WAR mule he deleted is made again",
     "file": "bible.html",
     "find": "        var _dl = (sh.warDeclined || []).indexOf('WAR' + n) >= 0;",
     "replace": "        var _dl = false;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - the board's mule is not one his delete can take back (no added flag, no mint id)",
     "file": "bible.html",
     "find": "      var m = { id: 'm' + Date.now().toString(36) + n, name: v.name, icon: '⚔️', note: 'war stash overflow - made by the board ' + at.slice(0, 10),\n                added: true, role: 'war', warN: n,\n",
     "replace": "      var m = { id: 'war-board-' + n, name: v.name, icon: '⚔️', note: 'war stash overflow - made by the board ' + at.slice(0, 10),\n                role: 'war', warN: n,\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - he is never tasked to make it in the game",
     "file": "bible.html",
     "find": "    var makes = (typeof _vaultWarMakeRows === 'function') ? _vaultWarMakeRows(built.records) : [];\n",
     "replace": "    var makes = [];\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - his tick is not recorded, so the task never leaves",
     "file": "bible.html",
     "find": "    m.inGame = { by: 'hand', at: new Date().toISOString() };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - an item read on WAR1 does not close the task",
     "file": "bible.html",
     "find": "    return !!(m && m.auto && !m.inGame && !_vaultMuleSeenInGame(m, recs || (window._moveModel || {}).records));\n",
     "replace": "    return !!(m && m.auto && !m.inGame);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2803 - his delete door forgets that he took the WAR mule back",
     "file": "bible.html",
     "find": "    try { _vaultWarDecline(m); } catch (eDl) {}\n",
     "replace": "",
     "matches": 1},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
