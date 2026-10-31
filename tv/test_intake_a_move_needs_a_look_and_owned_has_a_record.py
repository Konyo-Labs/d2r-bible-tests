# -*- coding: utf-8 -*-
"""AUTO INTAKE — a move needs a real look, and an owned item has its Vault record.

Elad, #230 (v3806 intake demo): Thresher was owned with no Vault record, and Treachery, a grand charm and the
Hellfire Torch each got a MOVE TASK on a read that the filing itself called "only 0 qualifying looks - needs 2".

Driven on the SHIPPED page through the real door (window.tvVaultRegister) with AUTO INTAKE on. The looks use the
live reader's own shape (vault_ledger witnesses): session s_<ms>_<n>, frame f_<ms>.jpg, lane, conf, cell.
  - a frame with no session is 0 looks: owned, a record, no move;
  - one session (even over several frames) is 1 look: one move (Elad 2026-10-27, test_an_auto_sighting_joins_the_manual_move);
    filing to a mule still needs 2 sessions;
  - two distinct sessions on the same cell are still ONE move, FROM that cell, TO a real target cell;
  - a second session on a later read joins the same row, it does not open a second one;
  - inventory / equipped stay locked (no move) and still have a record;
  - a base the TV registered (Thresher) is owned AND has a record.
NO CHROME AT ALL = a declared skip, never a pass.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_a_sweep_never_reticks_what_he_unticked as H  # noqa: E402

_B = {}

READ = r"""
function recs(){ try { return (JSON.parse(LSR.getItem('d2r_vaultRecords') || '{}').records || []); } catch (e) { return []; } }
function rowsOf(nm){ return recs().filter(function(r){ return r.name === nm; }); }
function movesOf(nm){ return rowsOf(nm).filter(function(r){ return r.move; }).map(function(r){ return r.move; }); }
function look(s, f, lane, cell, conf){ return { session: s, frame: f, lane: lane, conf: conf == null ? 0.9 : conf, cell: cell }; }
function reg(nm, lane, cell, looks, extra){
  var w = Object.assign({ lane: lane, location: lane, cell: cell, witnesses: looks }, extra || {});
  var r = window.tvVaultRegister(nm, w);
  try { if (typeof window._vaultMoveCollect === 'function') window._vaultMoveCollect(); } catch (e) {}
  try { if (typeof window.renderVault === 'function') window.renderVault(); } catch (e) {}
  return { ok: r && r.ok, refused: r && r.refused, label: r && r.label };
}
function state(nm){
  var owned = []; try { owned = JSON.parse(LSR.getItem('d2r_owned') || '[]'); } catch (e) {}
  var pv = {}; try { pv = JSON.parse(LSR.getItem('d2r_vaultProv') || '{}') || {}; } catch (e) {}
  var p = pv[nm] || null;
  return { owned: owned.indexOf(nm) >= 0, records: rowsOf(nm).length, moves: movesOf(nm),
           rows: rowsOf(nm).map(function(r){ return { copyIx: r.copyIx || 0, move: r.move || null, sight: r.sight || null }; }),
           prov: p ? { kind: p.kind || null, by: p.by || null, mule: p.mule || null,
                       ownedBy: p.ownedBy ? { kind: p.ownedBy.kind || null, by: p.ownedBy.by || null } : null } : null };
}
"""

S1 = 's_1791232871109_10831'
S2 = 's_1791239851249_40429'


def board():
    if "b" not in _B:
        _B["b"] = H.Board().open()
    return _B["b"]


def tearDownModule():
    b = _B.pop("b", None)
    if b is not None:
        b.close()


def fresh():
    board().seed({"d2r_owned": [], "d2r_vaultProv": {}, "d2r_muleAssign": {}, "d2r_vaultRecords": None})


def run(js):
    return board().run(READ + "window._vaultAutoIntakeSet(true);" + js)


class IntakeTwoLooks(unittest.TestCase):
    def setUp(self):
        try:
            board()
        except Exception as e:  # no chrome
            raise unittest.SkipTest("no Chrome: %s" % e)
        fresh()

    def test_a_frame_with_no_session_is_zero_looks_and_opens_no_move(self):
        # #202 (his 2026-10-27 ruling): a read with no look registers nothing - not owned, no move
        o = run("OUT.r = reg('Treachery', 'stash', 'stash:c3r4', [{ frame: 'f_1791233980015.jpg', lane: 'stash', cell: 'stash:c3r4' }]);"
                "OUT.s = state('Treachery');")
        self.assertFalse(o["r"]["ok"], o)
        self.assertEqual(o["r"]["refused"], "no-look", o)
        self.assertFalse(o["s"]["owned"], o)
        self.assertEqual(o["s"]["moves"], [], o)

    def test_the_v3806_demo_read_a_bare_frame_on_a_cell_opens_no_move(self):
        o = run("var w = { frame: 'f_1791233980015.jpg', location: 'stash', cell: 'stash:c3r4' };"
                "window.tvVaultRegister('Treachery', w); window.tvVaultRegister('Hellfire Torch',"
                " { frame: 'f_1791659194471.jpg', location: 'shared', cell: 'shared:c9r6' });"
                "try { window._vaultMoveCollect && window._vaultMoveCollect(); } catch (e) {}"
                "OUT.t = state('Treachery'); OUT.h = state('Hellfire Torch');")
        for k in ("t", "h"):
            self.assertFalse(o[k]["owned"], "#202: a bare frame registered an item: %r" % o)
            self.assertEqual(o[k]["moves"], [], o)

    def test_one_session_over_three_frames_is_one_look_and_one_move(self):
        # #202 Q2 (his default): an item ALREADY his still opens one move on one session
        board().seed({"d2r_owned": ["Hellfire Torch"], "d2r_vaultProv": {}, "d2r_muleAssign": {}, "d2r_vaultRecords": None})
        o = run("OUT.r = reg('Hellfire Torch', 'shared', 'shared:c9r6', ["
                "look('s_1791547225746_227', 'f_1791548118549.jpg', 'shared', 'shared:c9r6'),"
                "look('s_1791547225746_227', 'f_1791548119559.jpg', 'shared', 'shared:c9r6'),"
                "look('s_1791547225746_227', 'f_1791548120521.jpg', 'shared', 'shared:c9r6')]);"
                "OUT.s = state('Hellfire Torch');")
        self.assertTrue(o["s"]["owned"], o)
        self.assertEqual(len(o["s"]["moves"]), 1, o)
        self.assertEqual(o["s"]["moves"][0]["from"]["cell"], "shared:c9r6", o)
        self.assertTrue(o["s"]["moves"][0]["to"].get("cell"), o)

    def test_two_sessions_on_one_cell_open_one_move_from_that_cell_to_a_target(self):
        o = run("OUT.r = reg('Sharp Grand Charm of Vita', 'stash', 'stash:c2r1', ["
                "look('%s', 'f_1791233195777.jpg', 'stash', 'stash:c2r1', 0.85),"
                "look('%s', 'f_1791239854075.jpg', 'stash', 'stash:c2r1', 0.8)]);"
                "OUT.s = state('Sharp Grand Charm of Vita');" % (S1, S2))
        mv = o["s"]["moves"]
        self.assertEqual(len(mv), 1, o)
        self.assertEqual(mv[0]["from"]["cell"], "stash:c2r1", o)
        self.assertTrue(mv[0]["to"] and mv[0]["to"].get("cell"), o)
        self.assertEqual(mv[0]["status"], "to-move", o)

    def test_a_second_session_on_a_later_read_joins_the_same_row(self):
        # #202: an item already his, so the first read records its row (a new item is held until its second session)
        board().seed({"d2r_owned": ["Treachery"], "d2r_vaultProv": {}, "d2r_muleAssign": {}, "d2r_vaultRecords": None})
        o = run("OUT.a = reg('Treachery', 'stash', 'stash:c3r4', [look('%s', 'f_1791233980015.jpg', 'stash', 'stash:c3r4')]);"
                "OUT.s1 = state('Treachery');"
                "OUT.b = reg('Treachery', 'stash', 'stash:c3r4', [look('%s', 'f_1791239854999.jpg', 'stash', 'stash:c3r4')]);"
                "OUT.s2 = state('Treachery');" % (S1, S2))
        r1, r2 = o["s1"]["rows"], o["s2"]["rows"]
        self.assertEqual(len(r1), 1, o)
        self.assertEqual(len(r2), 1, o)                      # no second copy, no second row
        self.assertEqual(r2[0]["copyIx"], r1[0]["copyIx"], o)
        self.assertEqual(r1[0]["sight"]["witnesses"], 1, o)
        self.assertEqual(r2[0]["sight"]["witnesses"], 2, o)  # the second session joined THIS row
        m1, m2 = r1[0]["move"], r2[0]["move"]
        self.assertTrue(m1 and m2, o)
        self.assertEqual(m2["from"]["cell"], "stash:c3r4", o)
        self.assertEqual(m2["from"]["cell"], m1["from"]["cell"], o)
        self.assertEqual(m2["to"], m1["to"], o)                # same target
        self.assertTrue(m2["to"].get("cell"), o)
        self.assertEqual(m2["status"], "to-move", o)

    def test_inventory_and_equipped_have_a_record_and_no_move(self):
        # v3849 (dbc02a1c1): Horadric Cube is on the intake denylist (a panel word, never an item), so the inventory item is a charm
        o = run("reg('Annihilus', 'inventory', 'inventory:c0r0', [look('%s', 'f_1791233340172.jpg', 'inventory', 'inventory:c0r0'),"
                " look('%s', 'f_1791234901836.jpg', 'inventory', 'inventory:c0r0')]);"
                "reg('Vampire Gaze', 'equipped', 'equipped:head', [look('%s', 'f_1791239848059.jpg', 'equipped', 'equipped:head'),"
                " look('%s', 'f_1791239849135.jpg', 'equipped', 'equipped:head')], { holder: 'Konyo' });"
                "OUT.cube = state('Annihilus'); OUT.gaze = state('Vampire Gaze');" % (S1, S2, S1, S2))
        for k in ("cube", "gaze"):
            self.assertTrue(o[k]["owned"], o)
            self.assertGreaterEqual(o[k]["records"], 1, o)
            self.assertEqual(o[k]["moves"], [], o)

    def test_a_base_the_tv_registered_is_owned_and_has_a_record(self):
        # #202: one session holds it; the second registers it
        o = run("OUT.r = reg('Thresher', 'stash', 'stash:c7r1', [look('s_1791356557071_58418', 'f_1791358157119.jpg', 'stash', 'stash:c7r1', 0.85)]);"
                "OUT.s0 = state('Thresher');"
                "OUT.r2 = reg('Thresher', 'stash', 'stash:c7r1', [look('s_1791473772294_11798', 'f_1791474195360.jpg', 'stash', 'stash:c7r1', 0.8)]);"
                "OUT.s = state('Thresher');")
        self.assertFalse(o["s0"]["owned"], "#202: one session registered Thresher: %r" % o)
        self.assertEqual(o["r"]["refused"], "one-session", o)
        self.assertTrue(o["s"]["owned"], o)
        self.assertGreaterEqual(o["s"]["records"], 1, o)


    def test_a_base_filed_after_two_real_sessions_keeps_its_record(self):
        # real ledger looks: Thresher seen at c7r1 in one reel and c8r1 in a later one;
        # the second look files it and the filing prov keeps the owned stamp under ownedBy
        o = run("OUT.r = reg('Thresher', 'stash', 'stash:c7r1', [look('s_1791356557071_58418', 'f_1791358157119.jpg', 'stash', 'stash:c7r1', 0.85)]);"
                "OUT.r2 = reg('Thresher', 'stash', 'stash:c8r1', [look('s_1791473772294_11798', 'f_1791474195360.jpg', 'stash', 'stash:c8r1', 0.8)]);"
                "OUT.s = state('Thresher');")
        self.assertTrue(o["s"]["owned"], o)
        self.assertGreaterEqual(o["s"]["records"], 1, o)


    def test_the_owned_stamp_is_persisted_and_survives_filing(self):
        o = run("OUT.r = reg('Thresher', 'stash', 'stash:c7r1', [look('s_1791356557071_58418', 'f_1791358157119.jpg', 'stash', 'stash:c7r1', 0.85)]);"
                "OUT.s1 = state('Thresher');"
                "OUT.r2 = reg('Thresher', 'stash', 'stash:c7r1', [look('s_1791473772294_11798', 'f_1791474195360.jpg', 'stash', 'stash:c7r1', 0.8)]);"
                "OUT.s2 = state('Thresher');")
        p1, p2 = o["s1"]["prov"], o["s2"]["prov"]
        self.assertIsNone(p1, "#202: the first session wrote a receipt for an item that is not his yet: %r" % o)
        self.assertTrue(p2["mule"], o)                        # 2 sessions filed it
        self.assertEqual(p2["ownedBy"], {"kind": "owned", "by": "tvVaultRegister"}, o)
        self.assertGreaterEqual(o["s2"]["records"], 1, o)

    def test_a_zero_look_read_does_not_touch_a_stored_row(self):
        # a stored hand row with no FROM cell yet: a frame with no session must not fill it in
        board().seed({"d2r_owned": ["Treachery"], "d2r_vaultProv": {}, "d2r_muleAssign": {}, "d2r_vaultRecords": None})
        o = run("window._vaultMoveAdd ? 0 : 0;"
                "OUT.a = reg('Treachery', 'stash', 'stash:c3r4', [look('%s', 'f_1791233980015.jpg', 'stash', 'stash:c3r4')]);"
                "OUT.s1 = state('Treachery');"
                "OUT.b = reg('Treachery', 'stash', 'stash:c5r5', [{ frame: 'f_1791233980999.jpg', lane: 'stash', cell: 'stash:c5r5' }]);"
                "OUT.s2 = state('Treachery');" % S1)
        self.assertEqual(len(o["s1"]["moves"]), 1, o)
        self.assertEqual([m["from"]["cell"] for m in o["s2"]["moves"]], ["stash:c3r4"], o)

    def test_a_bad_prov_row_never_drops_the_other_base_records(self):
        board().seed({"d2r_owned": [], "d2r_vaultProv": {"Gothic Axe": {"ownedBy": "owned"}, "Giant Thresher": {"ownedBy": [1]},
                                                         "Great Axe": None, "Ogre Axe": 7},
                      "d2r_muleAssign": {}, "d2r_vaultRecords": None})
        o = run("OUT.r = reg('Thresher', 'stash', 'stash:c7r1', [look('s_1791356557071_58418', 'f_1791358157119.jpg', 'stash', 'stash:c7r1', 0.85),"
                " look('s_1791473772294_11798', 'f_1791474195360.jpg', 'stash', 'stash:c7r1', 0.8)]);"
                "OUT.s = state('Thresher');")
        self.assertTrue(o["s"]["owned"], o)
        self.assertGreaterEqual(o["s"]["records"], 1, o)


if __name__ == "__main__":
    unittest.main()
