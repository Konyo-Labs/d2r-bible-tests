# -*- coding: utf-8 -*-
"""REG-3101 (#153, agent-111's whole-page audit) - A WAR MULE THE BOARD MADE FOR AN OVERFLOW THAT IS GONE IS NO LONGER A TASK.

His ruling 2026-10-28: the board creates WAR<n> when the shared pages overflow and tasks him to make it in the game. MEASURED
on claude/int (whole page in node, the real doors): Shako x3 made WAR-A with "Create mule WAR-A in the game - the board made
it (...); the moves to it are below". He removed the Shako (vaultRemove) - no move row went to WAR-A any more - and the line
stayed, still saying the moves to it were below: a task with nothing behind it, on the tasks badge.

Now a make row is asked whether anything he owns lands on its mule (an open or done move row, or a name filed on it). A
board-made war mule with nothing landing on it loses its make line, and MOVE TASKS says why in its place ("WAR-A - no longer
needed: its overflow is gone ..."), never silently. His hand always wins: a war mule he made in the game, or renamed, keeps
what it had. v3864 - his ruling 2026-11-05 (d): the board now TAKES BACK a war mule it made that nothing lands on (and says
so), and a war mule he made in the game becomes his "Delete in the game" task; it is never removed by the board. The
CHARMS mule's line is not an overflow's and is untouched. His un-own's undo (vaultRestoreLast) brings the line back, because
the line is read off the plan on every paint.

Never a browser: the whole page runs in node (vault_page_node). The rename door is async (its prompt and the save), so a
world that renames holds the harness's one OUT line and writes it when the doors settle. RED_PROOF below.
"""
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
SHAKO = "Harlequin Crest (Shako)"      # big war gear: the war cap keeps 1, the other copies need a war mule

ASYNC = r"""
var __w = process.stdout.write.bind(process.stdout), __held = false;
process.stdout.write = function(s){ if (!__held && String(s).indexOf('__VAULT_PAGE_NODE_OUT__') >= 0) { __held = true; return true; } return __w(s); };
function done(){ process.stdout.write = __w; __w('\n__VAULT_PAGE_NODE_OUT__' + JSON.stringify(OUT) + '\n'); }
"""
BASE = r"""
var W = window, SH = %s;
function stored(){ return JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]'); }
function wars(){ return stored().filter(function(m){ return W._vaultWarRole(m) > 0; }); }
function paint(){ W.renderVault(); H.flush(60, 3); W.renderVault(); }
function list(){ return (document.getElementById('vault-move-list') || {}).innerHTML || ''; }
function makeRows(){ return (list().match(/<li class="vtk-line vtk-make"[\s\S]*?<\/li>/g) || []).map(function(x){ return x.replace(/<[^>]+>/g, ''); }); }
function goneRows(){ return (list().match(/<p class="vtk-make-gone"[\s\S]*?<\/p>/g) || []).map(function(x){ return x.replace(/<[^>]+>/g, ''); }); }
function unmakeRows(){ return (list().match(/<li class="vtk-line vtk-unmake"[\s\S]*?<\/li>/g) || []).map(function(x){ return x.replace(/<[^>]+>/g, ''); }); }
function look(){ return { owned: owned.has(SH), wars: wars().map(function(m){ return m.name; }), make: makeRows(), gone: goneRows(), unmake: unmakeRows(),
  badge: (document.getElementById('vault-tasks-n') || {}).textContent || '' }; }
window.uiConfirm = function(){ return Promise.resolve(true); };
W._vaultAutoIntakeSet(false);
OUT.name = W._vaultWarName(1);
[SH, SH, SH].forEach(function(n){ W.vaultHandAdd(n); }); paint();
OUT.a = look();
var _war = wars()[0] || {};
""" % json.dumps(SHAKO)
GONE = BASE + r"""
OUT.rm = !!(W.vaultRemove([SH], { why: 'he sold it' }) || {}).batch; paint();
OUT.b = look();
OUT.r = W.vaultRestoreLast(); paint();
OUT.r = OUT.r ? { restored: OUT.r.restored, why: OUT.r.why || null } : null;
OUT.c = look();
"""
COPIES = BASE + r"""
OUT.out2 = (W.vaultRemoveCopy(SH, 2, 'traded') || {}).ok; paint();
OUT.out1 = (W.vaultRemoveCopy(SH, 1, 'traded') || {}).ok; paint();
OUT.copies = copyCount(SH);
OUT.b = look();
"""
IN_GAME = BASE + r"""
OUT.ticked = (W._vaultWarMadeInGame(_war.id) || {}).ok; paint();
W.vaultRemove([SH], { why: 'he sold it' }); paint();
OUT.b = look();
"""
FILED = BASE + r"""
W.vaultHandAdd('Arreat\'s Face'); OUT.filed = (W.vaultAssign('Arreat\'s Face', _war.id) || {}); paint();
OUT.filed = { ok: OUT.filed.ok !== false, why: OUT.filed.why || null };
W.vaultRemove([SH], { why: 'he sold it' }); paint();
OUT.c = look();
"""
SEEDED = r"""
var W = window, SH = %s;
function list(){ return (document.getElementById('vault-move-list') || {}).innerHTML || ''; }
W.renderVault(); H.flush(60, 3); W.renderVault();
OUT.wars = JSON.parse(W.LSR.getItem('d2r_muleRoster') || '[]').filter(function(m){ return W._vaultWarRole(m) > 0; }).map(function(m){ return m.name; });
OUT.name = W._vaultWarName(1);
OUT.make = (list().match(/<li class="vtk-line vtk-make"[\s\S]*?<\/li>/g) || []).map(function(x){ return x.replace(/<[^>]+>/g, ''); });
OUT.gone = (list().match(/<p class="vtk-make-gone"[\s\S]*?<\/p>/g) || []).length;
OUT.records = W.LSR.getItem('d2r_vaultRecords');
""" % json.dumps(SHAKO)
SEED_STORES = ("localStorage.setItem('d2r_owned', %s);\nlocalStorage.setItem('d2r_copies', %s);\n"
               % (json.dumps(json.dumps([SHAKO])), json.dumps(json.dumps({SHAKO: 3}))))
RENAMED = ASYNC + BASE + r"""
window.prompt = function(){ return 'Barbie'; };                 /* his rename: a character's name */
(async function(){
  await W.vaultRenameMule(_war.id); paint();
  W.vaultRemove([SH], { why: 'he sold it' }); paint();
  OUT.b = look();
})().catch(function(e){ OUT.err = String(e && e.stack || e); }).then(done);
"""


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AWarMuleWhoseOverflowIsGoneIsNoLongerATask(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.w = {k: VPN.run(v, prelude=CLAIM, timeout=300)
                 for k, v in (("gone", GONE), ("copies", COPIES), ("ingame", IN_GAME), ("filed", FILED), ("renamed", RENAMED))}
        cls.seeded = VPN.run(SEEDED, prelude=CLAIM + SEED_STORES, timeout=300)

    def _ok(self, o):
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertNotIn("err", o, o.get("err"))
        a = o["a"]
        self.assertEqual(a["wars"], [o["name"]], "PREMISE: the board did not make %s for Shako x3: %r" % (o["name"], a))
        self.assertTrue([t for t in a["make"] if ("Create mule %s in the game" % o["name"]) in t], "PREMISE: no make line: %r" % a)
        self.assertEqual(a["gone"], [], "PREMISE: a needed war mule was said to be gone: %r" % a)

    def _war_make(self, look, name):
        return [t for t in look["make"] if ("Create mule %s in the game" % name) in t]

    def test_his_un_own_ends_the_make_task_and_says_why(self):
        o = self.w["gone"]
        self._ok(o)
        b = o["b"]
        self.assertTrue(o["rm"] and b["owned"] is False, "PREMISE: the Shako was not removed: %r" % b)
        self.assertEqual(self._war_make(b, o["name"]), [], "the make task stayed after its overflow was gone: %r" % b["make"])
        # v3864 - his ruling 2026-11-05 (d): a war mule the board made lives only while the shared stash overflows. The board
        # takes it back (it had been "his call", REG-3101) and says so; the CHARMS mule and his hand are untouched.
        self.assertTrue([g for g in b["gone"] if g.startswith("The board removed") and o["name"] in g],
                        "the war mule left without a word: %r" % b["gone"])
        self.assertEqual(b["wars"], [], "a war mule the board made for an overflow that is gone is still on the roster: %r" % b["wars"])

    def test_the_charms_mule_keeps_its_line(self):
        b = self.w["gone"]["b"]
        self.assertTrue([t for t in b["make"] if "Create mule CHARMS in the game" in t],
                        "the CHARMS mule lost its make line - it is no overflow's: %r" % b["make"])

    def test_his_undo_brings_the_make_task_back(self):
        o = self.w["gone"]
        self._ok(o)
        c = o["c"]
        self.assertTrue(c["owned"], "PREMISE: the undo did not put the Shako back: %r %r" % (o["r"], c))
        self.assertTrue(self._war_make(c, o["name"]), "the undo brought the Shako back but not its make task: %r" % c["make"])
        self.assertEqual(c["gone"], [], c["gone"])

    def test_two_copies_taken_out_leave_no_overflow_and_no_task(self):
        o = self.w["copies"]
        self._ok(o)
        self.assertEqual((o["out2"], o["out1"], o["copies"]), (True, True, 1), "PREMISE: two copies did not leave: %r" % o)
        self.assertEqual(self._war_make(o["b"], o["name"]), [], "one Shako left, still a make task: %r" % o["b"]["make"])
        self.assertTrue([g for g in o["b"]["gone"] if o["name"] in g], o["b"]["gone"])
        self.assertEqual(o["b"]["wars"], [], "two copies out, the overflow is gone, and the board kept the war mule: %r" % o["b"]["wars"])

    def test_a_war_mule_he_made_in_the_game_is_never_said_gone(self):
        o = self.w["ingame"]
        self._ok(o)
        self.assertTrue(o["ticked"], "PREMISE: his tick did not take")
        self.assertEqual(o["b"]["gone"], [], "a mule he made in the game was said removed: %r" % o["b"])
        # v3864 - his ruling (d): one he made in the game is never removed by the board; it is his task to delete it there
        self.assertEqual(o["b"]["wars"], [o["name"]], "the board removed a war mule he had made in the game: %r" % o["b"]["wars"])
        self.assertTrue([u for u in o["b"]["unmake"] if ("Delete mule %s in the game" % o["name"]) in u],
                        "a war mule he made in the game that nothing lands on is not his task to delete: %r" % o["b"])

    def test_something_filed_on_it_keeps_the_task(self):
        o = self.w["filed"]
        self._ok(o)
        self.assertTrue(o["filed"]["ok"], "PREMISE: the filing was refused: %r" % o["filed"])
        # v3864 - something he filed on it keeps it needed after the overflow goes: never taken back, its task stays
        self.assertEqual(o["c"]["wars"], [o["name"]], "the board took back a war mule something he owns is filed on: %r" % o["c"])
        self.assertTrue(self._war_make(o["c"], o["name"]),
                        "an item he filed on the war mule did not keep its make task: %r" % o["c"])
        self.assertEqual(o["c"]["gone"], [], o["c"]["gone"])

    def test_an_overflow_the_plan_holds_with_no_move_record_yet_keeps_its_task(self):
        """Shako x3 seeded straight into his stores (no hand add, so no move record yet): the war stash's own plan puts the
        extra copies on the war mule the board makes, so its make task is needed - REG-2803's declined world is this shape."""
        o = self.seeded
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertEqual(o["wars"], [o["name"]], "PREMISE: the board did not make %s: %r" % (o["name"], o))
        self.assertTrue([t for t in o["make"] if ("Create mule %s in the game" % o["name"]) in t],
                        "a war mule the plan fills was called no longer needed: %r (gone lines %d)" % (o["make"], o["gone"]))
        self.assertEqual(o["gone"], 0)

    def test_a_war_mule_he_renamed_is_his_hand_and_keeps_its_task(self):
        o = self.w["renamed"]
        self._ok(o)
        b = o["b"]
        self.assertTrue([t for t in b["make"] if "Create mule Barbie in the game" in t or "Create mule BARBIE in the game" in t],
                        "a war mule he named by hand lost its make task: %r" % b["make"])
        self.assertEqual(b["gone"], [], b["gone"])


# v3864 - REG-3101's two red-proofs (the make filter, and its "no longer needed" words) are RETIRED: his ruling (d) has
# the board take the mule back, so on an owner's board those lines no longer decide anything a law can see. They are the
# fallback for a REFUSED take-back (a shadow, a guest world, a held mule store), which this harness cannot reach: the
# page's own boot paint takes WAR-A back first. Recorded in BUGS REG-3180 as a gap, not a pass.
RED_PROOF = [
    {"why": "REG-3101 - a war mule he renamed is called no longer needed", "file": "bible.html", "find": "    if (m.name !== _vaultWarName(wn) && m.name !== 'WAR' + wn) return true;   /* a name he gave it: his hand */\n", "replace": "", "matches": 1, "needs": "node"},
    {"why": "REG-3101 - every make row is asked, not only a war mule's under the board's name: CHARMS loses its make task", "file": "bible.html", "find": "    if (!wn || m.id == null) return true;\n    if (m.name !== _vaultWarName(wn) && m.name !== 'WAR' + wn) return true;   /* a name he gave it: his hand */\n", "replace": "    if (m.id == null) return true;\n", "matches": 1, "needs": "node"},
    {"why": "REG-3101 - the war stash's plan is not asked: an overflow with no move record yet loses its make task", "file": "bible.html", "find": "      if (Object.keys(plan).some(function(k){ var p = plan[k]; return !!(p && p.id === m.id && owned.has(k.split('\\u0000')[0])); })) return true;\n", "replace": "", "matches": 1, "needs": "node"},
    {"why": "REG-3101 - his filing is not asked: an item he filed on the war mule does not keep its task", "file": "bible.html", "find": "    try { return Object.keys(assign || {}).some(function(n){ return assign[n] === m.id && owned.has(n); }); } catch (eA) { return true; }\n", "replace": "    return false;\n", "matches": 1, "needs": "node"},
    {"why": "v3864 (his ruling (d)) - the board keeps a war mule it made after its overflow is gone", "file": "bible.html", "find": "    var drop = _vaultWarIdle().filter(function(m){ return !m.inGame; });\n", "replace": "    var drop = [];\n", "matches": 1, "needs": "node"},
    {"why": "v3864 (his ruling (d)) - a war mule he made in the game that nothing lands on is not his task to delete", "file": "bible.html", "find": "    var _idleIn = (typeof _vaultWarIdle === 'function') ? _vaultWarIdle().filter(function(m){ return !!m.inGame; }) : [];\n", "replace": "    var _idleIn = [];\n", "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
