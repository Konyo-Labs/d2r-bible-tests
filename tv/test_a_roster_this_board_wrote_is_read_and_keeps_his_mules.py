# -*- coding: utf-8 -*-
"""REG-2522 FIX ROUND (V1 round 3; the review of REG-2522, major) - A ROSTER THIS BOARD WROTE IS READ, HIS MULES KEPT, AND A
ROSTER THAT IS HELD COMES BACK WITH HIS MULES, NEVER RENAMED TO THEIR IDS.

REG-2522 quarantined every saved roster that lacked a DEFAULT_ROSTER locker and told him "every roster this board saves holds
them, so these bytes did not come from it". False: until REG-2195 (2026-10-14, b32f373f2) every locker but SHARED STASH had
a 🗑, and vaultDeleteMule saved the roster without it. Reviewer, on the track head (p1 / p1b): the ten core lockers without
'wip' plus his mule {id:'m1k9zq2x', name:'WAR-1', added, boundChar:'Konyo'} -> quarantined, the whole vault held (every
register, vaultFile, the sorter, removals and + Add refused), the page drawing the 11 default lockers with WAR-1 gone; and
Start it fresh rebuilt the roster from the map's mule ids alone - WAR-1 came back as 'M1K9ZQ2X' (name, icon, note,
boundChar lost) and PVP-2, an added mule with no filing, was dropped.

NOW (bible.html ⟦VAULT HOLD⟧ and the migrations after it):
  * a core locker his roster lacks comes back at its default place, the v404 / v342.5 / v360 way, his own mules and notes
    kept and the roster saved - the vault is not held;
  * a roster is held only when the mule map still files items to a mule it lacks (_rosterMapWhy - the prune would drop
    them; the delete door takes a mule's filings with it), and while held the page shows his mules, rebuilt over the
    roster's own bytes and written nowhere;
  * Start it fresh rebuilds over the bytes kept aside (_vaultRosterFresh(raw)): every mule they list verbatim, every core
    locker, a stand-in for each mule the map names that they do not;
  * nothing saved yet + a map that files items to mules the default roster lacks: a stand-in for each, saved, no filing
    pruned (there are no bytes to keep aside).
The empty roster "[]" and another tab's write stay the REG-2522 law's (test_a_roster_without_its_core_lockers_is_unknown).

WHAT IS DRIVEN: the store door, the boot and its notice (Start it fresh), the tab sync, the vault module's head (load, the
hold, every migration), the shipped saveA / saveR and the W6 prune, cut from bible.html, in node. RED_PROOF below. A
missing node is the only skip.
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

import store_door_harness as D  # noqa: E402

PRUNE_A = "    var _pruneHeld = "
PRUNE_B = "    // v360 — shared-stash items"
CORE = ["sets-major", "sets-rest", "uni-weap", "uni-armor", "uni-small", "runewords", "bases", "magic-rare", "charms", "shared",
        "dupes", "wip"]   # REG-2895 - his 2026-10-28 ruling adds the CHARMS core locker
WAR1 = {"id": "m1k9zq2x", "name": "WAR-1", "icon": "⚔", "note": "my uber swap mule", "added": True, "boundChar": "Konyo"}
PVP2 = {"id": "m1k9zq3y", "name": "PVP-2", "icon": "🗡", "note": "pvp kit, worn only", "added": True, "boundChar": "Sorc"}
FILED = {"Grief": "uni-weap", "Harlequin Crest (Shako)": "uni-armor", "Enigma": "runewords", "Call to Arms": "m1k9zq2x"}


def _core(without=(), notes=True):
    return [{"id": i, "name": i.upper(), "icon": "x", "note": ("his note for " + i) if notes else ""}
            for i in CORE if i not in without]


def _pieces(s):
    return (D.stage(s) + D.boot(s) + D.tab_sync(s) + "\n" + "var renderVault = function(){};\n(function(){\n"
            + D.vault_head(s) + "\n" + D.fn(s, "saveA") + "\n" + D.fn(s, "saveR") + "\n"
            + "function muleById(id){ return roster.find(function(m){ return m.id === id; }); }\n"
            + "window.__prune = function(pool){ var poolAll = pool, _pvW6 = {};\n" + D.between(s, PRUNE_A, PRUNE_B, keep_b=False) + "\n};\n"
            + "window.__V = { saveA: saveA, assign: function(){ return assign; },"
            + " roster: function(){ return JSON.parse(JSON.stringify(roster)); } };\n})();\n")


PROBE = r"""
var q = window.LSR.quarantined('d2r_muleRoster');
OUT.q = q ? { kind: q.kind, reason: q.reason, aside: q.aside ? RAW[q.aside] : null } : null;
OUT.held = window._vaultBasisHeld();
OUT.roster = window.__V.roster();
OUT.saved = RAW['d2r_muleRoster'] == null ? null : RAW['d2r_muleRoster'];
window.__prune(Object.keys(window.__V.assign()));
OUT.map = JSON.parse(JSON.stringify(window.__V.assign()));
OUT.saveA = window.__V.saveA();
OUT.notice = (document.getElementById('store-quarantine') || {}).innerHTML || '';
"""


def _run(seed, more=""):
    s = D.src()
    return D.page(_pieces(s), PROBE + more, seed=seed)


def _seed(roster, filed=FILED):
    out = {"d2r_owned": json.dumps(sorted(filed)), "d2r_muleAssign": json.dumps(filed)}
    if roster is not None:
        out["d2r_muleRoster"] = json.dumps(roster)
    return out


def _ids(roster):
    return [m["id"] for m in roster]


def _by_id(roster):
    return dict((m["id"], m) for m in roster)


@unittest.skipIf(D.NODE is None, "node is absent - this law runs the SHIPPED vault module; UNMEASURED, not passing")
class ARosterThisBoardWroteIsReadAndKeepsHisMules(unittest.TestCase):

    def test_a_roster_saved_after_a_pre_reg_2195_delete_reads_and_gets_its_core_locker_back(self):
        """the reviewer's p1: the ten core lockers without WIP (deleted before 2026-10-14) plus his mule WAR-1"""
        o = _run(_seed(_core(without=("wip",)) + [WAR1]))
        self.assertIsNone(o["q"], "a roster this board wrote before REG-2195 was quarantined: %r" % o["q"])
        self.assertIsNone(o["held"], "the vault is held over a roster this board wrote: %r" % o["held"])
        self.assertEqual(_ids(o["roster"]), CORE + ["m1k9zq2x"], "WIP did not come back at its place, or WAR-1 moved")
        self.assertEqual(_by_id(o["roster"])["m1k9zq2x"], WAR1, "his mule lost its name, icon, note or boundChar")
        self.assertEqual(_by_id(o["roster"])["dupes"]["note"], "his note for dupes", "a note he wrote was replaced")
        saved = json.loads(o["saved"])
        self.assertEqual(_ids(saved), CORE + ["m1k9zq2x"], "the roster with WIP back was not saved")
        self.assertEqual(_by_id(saved)["m1k9zq2x"], WAR1)
        self.assertEqual(o["map"], FILED, "a filing was dropped: %r" % o["map"])
        self.assertTrue(o["saveA"], "the mule map is refused over a roster that reads")
        self.assertEqual(o["notice"], "", "a roster that reads is on the notice")

    def test_every_core_locker_it_lacks_comes_back_at_its_default_place(self):
        o = _run(_seed(_core(without=("wip", "dupes", "uni-small", "sets-major")) + [WAR1, PVP2]))
        self.assertIsNone(o["q"])
        self.assertEqual(_ids(o["roster"]), CORE + ["m1k9zq2x", "m1k9zq3y"],
                         "the core lockers did not come back in their places: %r" % _ids(o["roster"]))
        self.assertEqual(_by_id(o["roster"])["m1k9zq3y"], PVP2, "an added mule with no filing was not kept verbatim")
        self.assertEqual(_ids(json.loads(o["saved"])), CORE + ["m1k9zq2x", "m1k9zq3y"])

    def test_a_roster_the_map_disagrees_with_is_held_shows_his_mules_and_starts_fresh_with_them(self):
        """WAR-1 is gone from the saved roster while the map still files Call to Arms to it: held, never pruned against;
        Start it fresh keeps PVP-2 (no filing) and his notes, and a stand-in for WAR-1"""
        raw = json.dumps(_core() + [PVP2])
        more = r"""
window.__ASYNC = true;
window._storeStartFresh('d2r_muleRoster', true).then(function(r){
  OUT.fresh = r; OUT.freshSaved = RAW['d2r_muleRoster'] == null ? null : JSON.parse(RAW['d2r_muleRoster']);
  done();
});
"""
        o = _run(_seed(json.loads(raw)), more)
        self.assertIsNotNone(o["q"], "a roster that lacks a mule its map still files to was read as a roster")
        self.assertIn("m1k9zq2x", o["q"]["reason"], "the notice does not name the missing mule: %r" % o["q"]["reason"])
        self.assertIn("your mule map still files 1 item", o["q"]["reason"])
        self.assertEqual(o["q"]["aside"], raw, "the roster's exact bytes were not kept aside")
        self.assertTrue(o["held"] and "d2r_muleRoster" in o["held"], "the vault is not held: %r" % o["held"])
        self.assertEqual(o["saved"], raw, "a roster was saved over the bytes that are held")
        self.assertEqual(o["map"], FILED, "the prune dropped a filing against the held roster: %r" % o["map"])
        self.assertFalse(o["saveA"])
        mem = _by_id(o["roster"])
        self.assertEqual(mem.get("m1k9zq3y"), PVP2, "the held page does not show his own mule")
        self.assertIn("m1k9zq2x", mem, "the mule his map files to is not shown while held")
        self.assertEqual(mem["wip"]["note"], "his note for wip", "the held page shows default lockers, not his")
        self.assertTrue(o["fresh"]["ok"], o["fresh"])
        fresh = _by_id(o["freshSaved"])
        self.assertEqual(fresh.get("m1k9zq3y"), PVP2, "Start it fresh dropped or renamed his added mule with no filing")
        self.assertEqual(fresh["uni-weap"]["note"], "his note for uni-weap", "Start it fresh replaced his notes with defaults")
        self.assertIn("m1k9zq2x", fresh, "Start it fresh lost the mule his map files Call to Arms to")
        self.assertTrue(fresh["m1k9zq2x"].get("added"), "the stand-in is not a mule he can delete")
        self.assertEqual(sorted(set(CORE) - set(fresh)), [], "Start it fresh lost a core locker")

    def test_start_it_fresh_over_bytes_that_list_mules_and_a_stray_element_keeps_the_mules(self):
        raw = json.dumps(_core(without=("wip",)) + [WAR1, None])   # not a list of mules (the null) -> quarantined at read
        more = r"""
window.__ASYNC = true;
window._storeStartFresh('d2r_muleRoster', true).then(function(r){
  OUT.fresh = r; OUT.freshSaved = RAW['d2r_muleRoster'] == null ? null : JSON.parse(RAW['d2r_muleRoster']);
  done();
});
"""
        o = _run(_seed(json.loads(raw)), more)
        self.assertEqual((o["q"] or {}).get("reason"), "is not a list of mules", o["q"])
        self.assertTrue(o["fresh"]["ok"], o["fresh"])
        self.assertEqual(_ids(o["freshSaved"]), CORE + ["m1k9zq2x"], "Start it fresh did not rebuild over his bytes")
        self.assertEqual(_by_id(o["freshSaved"])["m1k9zq2x"], WAR1, "his mule came back renamed to its id")

    def test_nothing_saved_yet_and_a_map_that_files_to_an_added_mule_keeps_a_stand_in(self):
        o = _run(_seed(None))
        self.assertIsNone(o["q"], "an absent roster was quarantined (there are no bytes to keep aside)")
        self.assertIsNone(o["held"])
        self.assertIn("m1k9zq2x", _ids(o["roster"]), "no stand-in for the mule his map files Call to Arms to")
        self.assertEqual(o["map"], FILED, "the prune dropped a filing because nothing was saved for the roster")
        self.assertIn("m1k9zq2x", _ids(json.loads(o["saved"])), "the stand-in was not saved")


RED_PROOF = [
    {"why": "REG-2522 fix round - a core locker his roster lacks (a pre-REG-2195 delete) does not come back",
     "file": "bible.html", "matches": 1,
     "find": "    var back = _rosterPutCore(roster);\n    if (!back.length) return;\n",
     "replace": "    var back = [];\n    if (!back.length) return;\n"},
    {"why": "REG-2522 fix round - Start it fresh rebuilds the roster from the map's mule ids alone (WAR-1 -> 'M1K9ZQ2X')",
     "file": "bible.html", "matches": 1,
     "find": "        fresh = window._vaultRosterFresh(_keptRaw);\n",
     "replace": "        fresh = window._vaultRosterFresh(null);\n"},
    {"why": "REG-2522 fix round - a held roster draws the default lockers (his own mules vanish from the board)",
     "file": "bible.html", "matches": 1,
     "find": "    roster = _rosterRebuilt(roster);\n  })();\n",
     "replace": "    roster = DEFAULT_ROSTER.map(function(m){ return Object.assign({}, m); });\n  })();\n"},
    {"why": "REG-2522 fix round - a roster with nothing saved keeps no stand-in, so the prune drops the map's filings",
     "file": "bible.html", "matches": 1,
     "find": "    if (!_rosterSaved){\n      roster = _rosterRebuilt(roster);\n",
     "replace": "    if (!_rosterSaved){\n      return;\n"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
