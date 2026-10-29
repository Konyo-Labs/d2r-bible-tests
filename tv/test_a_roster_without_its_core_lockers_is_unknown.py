# -*- coding: utf-8 -*-
"""REG-2522 (V1 round 3; the review of REG-2411, rv6) - A MULE ROSTER THAT LACKS A CORE LOCKER IS UNKNOWN, NEVER A ROSTER.

The REG-2411 shape check asked only that every element of a saved roster is a mule - and every element of "[]" is. "[]"
is exactly the bytes REG-2414's merge bug stored, so it is the next value GrokBot's malformed-roster sweep tries. On load
the migrations saved a three-locker roster (runewords, magic-rare, shared) over it, the 8 core lockers (which cannot be
deleted, REG-2195) never came back, and the paint's W6 prune dropped every filing on uni-weap, uni-armor, the sets, the
dupes and the rest; saveA wrote the pruned map. Nothing quarantined, the vault not held, nothing said. A roster missing
one core locker did the same to that locker's filings. Reviewer, on the shipped head, migrations and prune: map
{Grief:uni-weap, Shako:uni-armor, Enigma:runewords} + roster "[]" -> quarantined [], held null, prune -> {Enigma:runewords},
saveA() true.

NOW (as narrowed by the REG-2522 fix round - "a roster without a core locker did not come from this board" was false:
until REG-2195 every locker but SHARED STASH had a delete button, so a pre-10-14 roster may lack WIP and must read; that
half is tv/test_a_roster_this_board_wrote_is_read_and_keeps_his_mules.py):
  * an EMPTY roster ("[]") is the wrong shape at the one reader (_muleShapeWhy): quarantined, bytes kept aside, vault held;
  * a roster that lacks a mule its MAP still files items to - uni-weap here, with Grief filed to it - is quarantined once
    both stores are read (_rosterMapWhy): the delete door takes a mule's filings with it, so the two disagree, and the
    prune drops nothing against them;
  * another tab's write is held to every core locker as well (_rosterCoreWhy) - no tab of this board saves one without.
His real roster - every core locker, his notes, his own mules - reads as before (measured on every ledger snapshot that
holds a roster: all hold the 11 core lockers, and no map names a mule its roster lacks).

WHAT IS DRIVEN: the store door, the boot, the tab sync, the vault module's head (load, the migrations, the hold), the
shipped saveA / saveR and the W6 prune, cut from bible.html, in node. RED_PROOF below. A missing node is the only skip.
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
FILED = {"Grief": "uni-weap", "Harlequin Crest (Shako)": "uni-armor", "Enigma": "runewords"}


def _roster(ids, extra=None):
    out = [{"id": i, "name": i.upper(), "icon": "x", "note": "his note for " + i} for i in ids]
    return out + (extra or [])


def _pieces(s):
    return (D.stage(s) + D.boot(s) + D.tab_sync(s) + "\n" + "var renderVault = function(){};\n(function(){\n"
            + D.vault_head(s) + "\n" + D.fn(s, "saveA") + "\n" + D.fn(s, "saveR") + "\n"
            + "function muleById(id){ return roster.find(function(m){ return m.id === id; }); }\n"
            + "window.__prune = function(pool){ var poolAll = pool, _pvW6 = {};\n" + D.between(s, PRUNE_A, PRUNE_B, keep_b=False) + "\n};\n"
            + "window.__V = { saveA: saveA, saveR: saveR, assign: function(){ return assign; },"
            + " ids: function(){ return roster.map(function(m){ return m.id; }); } };\n})();\n")


OTHER = ("function other(k, nv){ var ov = RAW[k] == null ? null : RAW[k]; if (nv == null) delete RAW[k]; else RAW[k] = String(nv);"
         " fire(k, ov, nv == null ? null : String(nv)); }\n")

PROBE = r"""
var q = window.LSR.quarantined('d2r_muleRoster');
OUT.q = q ? { kind: q.kind, reason: q.reason, aside: q.aside ? RAW[q.aside] : null, lastGood: !!q.lastGood } : null;
OUT.held = window._vaultBasisHeld();
OUT.ids = window.__V.ids();
window.__prune(Object.keys(window.__V.assign()).filter(function(n){ return n !== 'ghost item'; }));
OUT.map = JSON.parse(JSON.stringify(window.__V.assign()));
OUT.saveA = window.__V.saveA(); window.__V.saveR();
OUT.rawRoster = RAW['d2r_muleRoster'] == null ? null : RAW['d2r_muleRoster'];
OUT.rawMap = RAW['d2r_muleAssign'];
OUT.notice = (document.getElementById('store-quarantine') || {}).innerHTML || '';
"""


def _run(body, seed):
    s = D.src()
    return D.page(_pieces(s), OTHER + body, seed=seed)


def _seed(roster):
    out = {"d2r_owned": json.dumps(sorted(FILED)), "d2r_muleAssign": json.dumps(FILED)}
    if roster is not None:
        out["d2r_muleRoster"] = roster
    return out


@unittest.skipIf(D.NODE is None, "node is absent - this law runs the SHIPPED vault module; UNMEASURED, not passing")
class ARosterWithoutItsCoreLockersIsUnknown(unittest.TestCase):

    def _assert_held_and_kept(self, o, raw, why):
        self.assertIsNotNone(o["q"], "a roster %s was read as a roster" % why)
        self.assertEqual(o["q"]["kind"], "quarantine")
        self.assertEqual(o["q"]["aside"], raw, "the roster's exact bytes were not kept aside")
        self.assertTrue(o["held"] and "d2r_muleRoster" in o["held"], "the vault is not held: %r" % o["held"])
        self.assertEqual(sorted(o["ids"]), sorted(CORE), "the page does not run on the default lockers in memory")
        self.assertEqual(o["map"], FILED, "the prune dropped filings against a roster that would not read: %r" % o["map"])
        self.assertFalse(o["saveA"], "the mule map was written while the roster is UNKNOWN")
        self.assertEqual(o["rawRoster"], raw, "a roster was saved over the bytes that would not read")
        self.assertEqual(json.loads(o["rawMap"]), FILED)
        self.assertIn('data-store="d2r_muleRoster"', o["notice"], "the held roster is not on the board")

    def test_an_empty_roster_is_unknown_and_drops_no_filing(self):
        o = _run(PROBE, _seed("[]"))
        self._assert_held_and_kept(o, "[]", '"[]"')
        self.assertIn("holds no mules at all", o["q"]["reason"])
        self.assertNotIn("did not come from it", o["q"]["reason"], "the notice still claims what this board cannot know")

    def test_a_roster_missing_one_core_locker_is_unknown_and_its_filings_stay(self):
        raw = json.dumps(_roster([i for i in CORE if i != "uni-weap"]))
        o = _run(PROBE, _seed(raw))
        self._assert_held_and_kept(o, raw, "missing uni-weap")
        self.assertIn("uni-weap", o["q"]["reason"], "the notice does not say which locker is missing: %r" % o["q"]["reason"])
        self.assertIn("your mule map still files 1 item", o["q"]["reason"], "the notice does not say why: %r" % o["q"]["reason"])

    def test_his_roster_with_every_core_locker_and_his_own_mules_reads_as_before(self):
        raw = json.dumps(_roster(CORE, [{"id": "m1k9zq2x", "name": "WAR-1", "icon": "x", "note": "", "added": True,
                                         "boundChar": "Konyo"}]))
        # 'ghost item' is filed to a real mule, owned by no one and witnessed by nothing: the prune's premise case
        filed = dict(FILED, **{"Call to Arms": "m1k9zq2x", "ghost item": "uni-armor"})
        seed = {"d2r_owned": json.dumps(sorted(filed)), "d2r_muleAssign": json.dumps(filed), "d2r_muleRoster": raw}
        o = _run(PROBE, seed)
        self.assertIsNone(o["q"], "his real roster shape was quarantined: %r" % o["q"])
        self.assertIsNone(o["held"])
        self.assertIn("m1k9zq2x", o["ids"], "his own mule is gone from the roster")
        self.assertEqual(o["map"].get("Call to Arms"), "m1k9zq2x", "a filing on his own mule was dropped")
        self.assertNotIn("ghost item", o["map"], "PREMISE: the prune no longer drops an unowned, unwitnessed filing")
        self.assertTrue(o["saveA"])

    def test_another_tab_writing_a_roster_without_its_core_lockers_is_never_adopted(self):
        for label, bad in (("[]", "[]"), ("missing uni-weap", json.dumps(_roster([i for i in CORE if i != "uni-weap"])))):
            with self.subTest(written=label):
                o = _run("var before = RAW['d2r_muleRoster']; other('d2r_muleRoster', " + json.dumps(bad) + ");" + PROBE,
                         _seed(json.dumps(_roster(CORE))))
                self.assertIsNotNone(o["q"], "another tab's %s roster was adopted" % label)
                self.assertIn("another tab wrote a store of the wrong shape", o["q"]["reason"])
                self.assertEqual(sorted(o["ids"]), sorted(CORE), "this tab's roster was replaced by another tab's %s" % label)
                self.assertEqual(o["map"], FILED, "the prune dropped filings after another tab's %s roster" % label)
                self.assertTrue(o["q"]["lastGood"], "this tab's good roster is not offered back (Keep this tab's copy)")
                self.assertEqual(o["q"]["aside"], bad)


RED_PROOF = [
    {"why": "REG-2522 - an empty roster (\"[]\") reads as a roster again (three lockers -> the prune drops every filing)",
     "file": "bible.html", "matches": 1,
     "find": "    if (!v.length)\n      return 'holds no mules at all",
     "replace": "    if (false)\n      return 'holds no mules at all"},
    {"why": "REG-2522 - another tab's roster is merged without the roster's shape rule (\"[]\" adopted)",
     "file": "bible.html", "matches": 1,
     "find": "                             shape: function(v){ return _muleShapeWhy(RK, v) || _rosterCoreWhy(v); },\n",
     "replace": ""},
    {"why": "REG-2522 - the load reads the roster without the module's shape rule (the one reader asks no shape)",
     "file": "bible.html", "matches": 1,
     "find": "      var v0 = D.read(k, function(v){ return _muleShapeWhy(k, v); }, _LOAD_ABSENT);\n",
     "replace": "      var v0 = D.read(k, function(v){ return null; }, _LOAD_ABSENT);\n"},
    {"why": "REG-2522 fix round - a roster that lacks a mule its map still files items to is not held (the prune drops them)",
     "file": "bible.html", "matches": 1,
     "find": "    var why = _rosterMapWhy(roster, assign);\n    if (!why) return;\n",
     "replace": "    var why = null;\n    if (!why) return;\n"},
    {"why": "REG-2522 fix round - another tab's roster that lacks a core locker is adopted (its filings pruned)",
     "file": "bible.html", "matches": 1,
     "find": "shape: function(v){ return _muleShapeWhy(RK, v) || _rosterCoreWhy(v); },",
     "replace": "shape: function(v){ return _muleShapeWhy(RK, v); },"},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
