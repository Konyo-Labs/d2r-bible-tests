# -*- coding: utf-8 -*-
"""REG-2414 (review of REG-2413, reproduced) — A STORE ANOTHER TAB REMOVED IS ITS ABSENT VALUE, NEVER AN EMPTY ONE.

A storage event whose newValue is null is another document REMOVING the key: the footer's "Erase all saved progress"
(window.LSR.wipeProfile) removes every key one by one, and a harness or devtools removes one. ⟦TAB SYNC⟧ merged that as
an EMPTY container. The page reads an absent d2r_muleRoster as the default lockers, so the roster became [] in this tab,
the next paint's W6 prune found no mule for any filing and dropped every one, and the other tab's next filing made this
tab write the pruned map back: his mule map wiped with no action in this tab. saveR stored "[]", which a reload reads as a
roster (truthy), so the 8 other default lockers never came back. d2r_multiKeep did the same: a removal merged to {} and
persist() stored "{}", so the 9 MULTI_KEEP_DEFAULT targets were gone for good.

THE FIX, driven here on the SHIPPED ⟦TAB SYNC⟧ block, the boot loaders, persist(), the rwMade boot seed, the vault
module head (which registers the roster with its default and the vault stores), saveA / saveR and the W6 render prune,
in node, with the page's own storage listener fired as the browser fires it:
  · a removed store (and an absent value it replaced) is what a reload of this tab reads: the roster's default lockers,
    multiKeep's targets, the owner's forged-runeword seed (an empty Chronicle on a fresh profile), the empty container
    for every other store - in the merge, in a quarantine it lifts, and in the "same" check, so nothing is written back;
  · so the prune keeps every filing on a default locker, and the other tab's next filing never wipes the map;
  · a first save in another tab is merged against this tab's default, so a target it dropped does not come back;
  · a quarantined store another tab removed lifts, to its default (a 'store' kind lifts too);
  · "Erase all saved progress" in another tab leaves this tab exactly as a reload would, and this tab writes nothing.
The cross-tab delivery itself is the browser's: tests/reg2410_stores_never_bricked.spec.ts drives two pages on CI.
RED_PROOF below; prove with `HEART2_PROVE_WORKERS=1 python3 tv/heart2.py --prove test_a_store_another_tab_removed_reads_as_its_default`.
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

#: the W6 render prune, cut from renderVaultDraw the way the review cut it (its own words for "held")
PRUNE_A = "    var _pruneHeld = "
PRUNE_B = "    // v360 — shared-stash items"


def _line(s, start):
    """one whole line of bible.html, found by its unique start"""
    n = s.count("\n" + start)
    if n != 1:
        raise AssertionError("the line %r matched %d times - the anchor moved" % (start[:60], n))
    i = s.index("\n" + start) + 1
    return s[i:s.index("\n", i) + 1]


def _rw_boot(s):
    """the boot's own rwMade seed: the owner's Chronicle seed, the fresh-profile flag, and the line that seeds an absent store"""
    return (_line(s, "const _RWC_SEED = ") + _line(s, "var _rwFreshFlag = false;")
            + _line(s, "if (rwMade === null || typeof rwMade !== 'object' || Array.isArray(rwMade))"))


def _tab(s):
    return (D.stage(s) + "window._seedsBelongHere = true;\n" + D.boot(s) + _rw_boot(s) + D.tab_sync(s) + "\n"
            + "var renderVault = function(){};\n(function(){\n" + D.vault_head(s) + "\n"
            + D.fn(s, "saveA") + "\n" + D.fn(s, "saveR") + "\n"
            + "function muleById(id){ return roster.find(function(m){ return m.id === id; }); }\n"
            + "window.__prune = function(pool){ var poolAll = pool, _pvW6 = {};\n" + D.between(s, PRUNE_A, PRUNE_B, keep_b=False) + "\n};\n"
            + "window.__V = { saveA: saveA, saveR: saveR, roster: function(){ return roster; }, assign: function(){ return assign; },"
            + " ids: function(){ return roster.map(function(m){ return m.id; }); } };\n})();\n")


#: the other document writes `nv` over the key, or removes it (nv null) - the store moves first, then this tab hears it
OTHER = ("function other(k, nv){ var ov = RAW[k] == null ? null : RAW[k]; if (nv == null) delete RAW[k]; else RAW[k] = String(nv);"
         " fire(k, ov, nv == null ? null : String(nv)); }\n")
WRITES = ("var WROTE = []; var _set = window.LSR.setItem; window.LSR.setItem = function(k, v){ WROTE.push(k);"
          " return _set.call(window.LSR, k, v); };\n")
DEFAULT_IDS = ["sets-major", "sets-rest", "uni-weap", "uni-armor", "uni-small", "runewords", "bases", "magic-rare",
               "charms", "shared", "dupes", "wip"]   # REG-2895 - his 2026-10-28 charm ruling made CHARMS a core locker
FILED = {"Grief": "uni-weap", "Harlequin Crest (Shako)": "uni-armor", "Enigma": "runewords"}


def _run(body, seed):
    s = D.src()
    return D.page(_tab(s), OTHER + WRITES + body, seed=seed)


def _rw_seed_plus():
    """the owner's Chronicle seed as bible.html declares it, plus one word the seed lacks"""
    line = _line(D.src(), "const _RWC_SEED = ").strip()
    seed = json.loads(line[len("const _RWC_SEED = "):].rstrip(";"))
    seed["A Word Nobody Forged"] = "Oct 22, 2026 \u00b7 12:00"
    return json.dumps(seed)


def _seed(extra=None):
    out = {"d2r_owned": json.dumps(sorted(FILED)), "d2r_muleAssign": json.dumps(FILED)}
    for k, v in (extra or {}).items():
        out[k] = _rw_seed_plus() if v == "__SEED_PLUS__" else v
    return out


@unittest.skipIf(D.NODE is None, "node is absent - this law runs the SHIPPED tab sync; UNMEASURED, not passing")
class AStoreAnotherTabRemovedReadsAsItsDefault(unittest.TestCase):

    def test_the_roster_another_tab_removed_is_the_default_lockers_and_every_filing_stays(self):
        """The review's r3: one removal event, then the paint's prune, then this tab's own saves."""
        o = _run("RAW['d2r_muleRoster'] = JSON.stringify(window.__V.roster()); WROTE.length = 0;"
                 "OUT.before = window.__V.ids(); other('d2r_muleRoster', null);"
                 "OUT.after = window.__V.ids(); OUT.held = window.LSR.quarantined('d2r_muleRoster'); OUT.wrote = WROTE.slice();"
                 "window.__prune(Object.keys(window.__V.assign()));"
                 "OUT.pruned = JSON.parse(JSON.stringify(window.__V.assign()));"
                 "OUT.saveA = window.__V.saveA(); OUT.map = JSON.parse(RAW['d2r_muleAssign']);"
                 "window.__V.saveR(); OUT.rosterSaved = JSON.parse(RAW['d2r_muleRoster']).map(function(m){ return m.id; });",
                 _seed())
        self.assertEqual(o["before"], DEFAULT_IDS)
        self.assertEqual(o["after"], DEFAULT_IDS, "a removed roster must read as the default lockers, never []")
        self.assertIsNone(o["held"], "a removal of a roster this tab had not changed is taken, not held")
        self.assertEqual(o["wrote"], [], "taking the removal writes nothing back")
        self.assertEqual(o["pruned"], FILED, "the prune dropped filings against an emptied roster")
        self.assertTrue(o["saveA"])
        self.assertEqual(o["map"], FILED, "this tab wrote a pruned mule map over his filings")
        self.assertEqual(o["rosterSaved"], DEFAULT_IDS, "saveR stored a roster a reload would never read")

    def test_the_other_tabs_next_filing_does_not_wipe_the_map(self):
        """The review's r3b: the other tab, which still holds his map, files one more item after the removal."""
        o = _run("RAW['d2r_muleRoster'] = JSON.stringify(window.__V.roster());"
                 "other('d2r_muleRoster', null); window.__prune(Object.keys(window.__V.assign()));"
                 "var m = JSON.parse(RAW['d2r_muleAssign']); m['Arachnid Mesh'] = 'uni-armor';"
                 "other('d2r_muleAssign', JSON.stringify(m)); OUT.map = JSON.parse(RAW['d2r_muleAssign']);"
                 "OUT.mem = JSON.parse(JSON.stringify(window.__V.assign()));", _seed())
        want = dict(FILED, **{"Arachnid Mesh": "uni-armor"})
        self.assertEqual(o["map"], want, "the other tab's filing came back as a map with only its own row")
        self.assertEqual(o["mem"], want)

    def test_multikeep_another_tab_removed_is_the_default_targets(self):
        o = _run("var DEF = JSON.stringify(MULTI_KEEP_DEFAULT); WROTE.length = 0; other('d2r_multiKeep', null);"
                 "OUT.same = JSON.stringify(multiKeep) === JSON.stringify(Object.assign({}, MULTI_KEEP_DEFAULT));"
                 "OUT.n = Object.keys(multiKeep).length; OUT.grief = Object.prototype.hasOwnProperty.call(multiKeep, 'Grief');"
                 "OUT.wrote = WROTE.slice(); persist(); OUT.stored = JSON.parse(RAW['d2r_multiKeep']);"
                 "OUT.def = JSON.parse(DEF);",
                 _seed({"d2r_multiKeep": '{"Andariel\'s Visage":5,"Raven Frost":4,"Nagelring":4,"Harlequin Crest (Shako)":3,'
                                         '"Mara\'s Kaleidoscope":3,"The Stone of Jordan":3,"War Traveler":2,"Gore Rider":2,'
                                         '"Stormshield":2,"Grief":2}'}))
        self.assertTrue(o["same"], "a removed multiKeep must read as MULTI_KEEP_DEFAULT")
        self.assertEqual(o["n"], 9)
        self.assertFalse(o["grief"], "a target the removal took must not stay")
        self.assertEqual(o["wrote"], [], "the default it reads is what a reload reads, so nothing is written back")
        self.assertEqual(o["stored"], o["def"], "persist() stored {} - the 9 default targets would never come back")

    def test_a_first_save_in_the_other_tab_is_merged_against_this_tabs_default(self):
        """Nothing saved: this tab runs on the default targets. The other tab saves them with one dropped."""
        o = _run("var m = Object.assign({}, MULTI_KEEP_DEFAULT); delete m['Stormshield']; WROTE.length = 0;"
                 "other('d2r_multiKeep', JSON.stringify(m)); OUT.storm = Object.prototype.hasOwnProperty.call(multiKeep, 'Stormshield');"
                 "OUT.wrote = WROTE.slice(); OUT.n = Object.keys(multiKeep).length;", _seed())
        self.assertFalse(o["storm"], "a target the other tab dropped from the default came back here")
        self.assertEqual(o["n"], 8)
        self.assertEqual(o["wrote"], [], "this tab wrote the dropped target back over the other tab's save")

    def test_a_quarantined_roster_another_tab_removed_lifts_to_the_default_lockers(self):
        o = _run("OUT.before = window.LSR.quarantined('d2r_muleRoster') ? window.LSR.quarantined('d2r_muleRoster').kind : null;"
                 "other('d2r_muleRoster', null); OUT.after = window.LSR.quarantined('d2r_muleRoster');"
                 "OUT.ids = window.__V.ids(); OUT.unread = window._muleStoreUnread('d2r_muleRoster');",
                 _seed({"d2r_muleRoster": "{}"}))
        self.assertEqual(o["before"], "quarantine", "the setup must start with the roster quarantined here")
        self.assertIsNone(o["after"], "the bad bytes are gone from the key, so the quarantine lifts")
        self.assertEqual(o["ids"], DEFAULT_IDS, "a lifted roster must be the default lockers, never []")
        self.assertIsNone(o["unread"], "the module's own unread mark lifts with the door's")

    def test_a_vault_store_another_tab_removed_lifts_its_quarantine(self):
        """A 'store' kind (read from storage on every use): its quarantine lifts when the bad bytes are removed."""
        o = _run("window.LSR.quarantine('d2r_vaultProv', 'will not parse'); OUT.before = !!window.LSR.quarantined('d2r_vaultProv');"
                 "other('d2r_vaultProv', null); OUT.after = window.LSR.quarantined('d2r_vaultProv');"
                 "OUT.aside = Object.keys(aside());", _seed({"d2r_vaultProv": '{"Grief":{"mule":"uni-weap"'}))
        self.assertTrue(o["before"])
        self.assertIsNone(o["after"], "a vault store another tab removed stays quarantined here")
        self.assertEqual(len(o["aside"]), 1, "the bad bytes stay kept aside after the lift")

    def test_rwmade_another_tab_removed_is_the_owners_seed_or_a_fresh_chronicle(self):
        o = _run("var extra = 'A Word Nobody Forged'; WROTE.length = 0;"
                 "OUT.had = Object.prototype.hasOwnProperty.call(rwMade, extra);"
                 "other('d2r_rwMade', null); OUT.n = Object.keys(rwMade).length; OUT.seedN = Object.keys(_RWC_SEED).length;"
                 "OUT.extra = Object.prototype.hasOwnProperty.call(rwMade, extra); OUT.wrote = WROTE.slice();"
                 "RAW['d2r_rwMade'] = JSON.stringify(rwMade); RAW['d2r_rwProfile'] = 'fresh'; other('d2r_rwMade', null);"
                 "OUT.fresh = Object.keys(rwMade).length;",
                 _seed({"d2r_rwMade": "__SEED_PLUS__"}))
        self.assertTrue(o["had"], "the setup must start with a forged word the seed lacks")
        self.assertEqual(o["n"], o["seedN"], "a removed Chronicle must read as the owner's seed, as a reload reads it")
        self.assertFalse(o["extra"])
        self.assertEqual(o["wrote"], [])
        self.assertEqual(o["fresh"], 0, "on a fresh profile a removed Chronicle reads as empty, as a reload reads it")

    def test_erase_all_in_another_tab_leaves_this_tab_as_a_reload_would_and_writes_nothing(self):
        """LSR.wipeProfile in another tab: every key of this world removed one by one, each heard here."""
        o = _run("RAW['d2r_muleRoster'] = JSON.stringify(window.__V.roster()); WROTE.length = 0;"
                 "Object.keys(RAW).filter(function(k){ return k.indexOf('d2r_') === 0; }).forEach(function(k){ other(k, null); });"
                 "OUT.owned = owned.size; OUT.assign = JSON.parse(JSON.stringify(window.__V.assign())); OUT.ids = window.__V.ids();"
                 "OUT.mk = JSON.stringify(multiKeep) === JSON.stringify(Object.assign({}, MULTI_KEEP_DEFAULT));"
                 "OUT.copies = JSON.parse(JSON.stringify(copies)); OUT.runes = JSON.parse(JSON.stringify(runeStash));"
                 "OUT.wish = wishlist.size; OUT.rw = Object.keys(rwMade).length === Object.keys(_RWC_SEED).length;"
                 "OUT.wrote = WROTE.slice(); OUT.held = window.LSR.quarantined().map(function(q){ return q.key; });"
                 "OUT.left = Object.keys(RAW);",
                 _seed({"d2r_multiKeep": '{"Grief":2}', "d2r_copies": '{"Grief":2}', "d2r_runeStash": '{"Ber":1}',
                        "d2r_wishlist": '["Tyrael\'s Might"]', "d2r_rwMade": "__SEED_PLUS__"}))
        self.assertEqual(o["owned"], 0)
        self.assertEqual(o["assign"], {})
        self.assertEqual(o["ids"], DEFAULT_IDS, "an erased roster must read as the default lockers")
        self.assertTrue(o["mk"], "an erased multiKeep must read as its default targets")
        self.assertEqual((o["copies"], o["runes"], o["wish"]), ({}, {}, 0))
        self.assertTrue(o["rw"], "an erased Chronicle must read as the owner's seed")
        self.assertEqual(o["wrote"], [], "this tab wrote its copy back over the erase: %r" % o["wrote"])
        self.assertEqual(o["held"], [])
        self.assertEqual(o["left"], [], "the erase must leave nothing behind in this world")


RED_PROOF = [
    {"why": "REG-2414 - a removed roster is merged as [] (the review's r3: every filing pruned, the map wiped)",
     "file": "bible.html", "matches": 1,
     "find": "    var tl = tv, bl = base.ok ? valOf(base.v) : [];\n",
     "replace": "    var tl = theirs.v || [], bl = base.ok ? valOf(base.v) : [];\n"},
    {"why": "REG-2414 - a quarantine another tab removed lifts to an empty store, not its default",
     "file": "bible.html", "matches": 1,
     "find": "    replace(live, tv);\n    var rl = LSR.release(k);\n",
     "replace": "    replace(live, theirs.v);\n    var rl = LSR.release(k);\n"},
    {"why": "REG-2414 - no store has an absent value: every removal reads as an empty container",
     "file": "bible.html", "matches": 1,
     "find": "  var valOf = function(v){ return (v == null) ? absentOf() : v; };\n",
     "replace": "  var valOf = function(v){ return (v == null) ? ((spec.kind === 'set' || spec.kind === 'list') ? [] : {}) : v; };\n"},
    {"why": "REG-2414 - multiKeep loses its absent value: a removal stores {} and the 9 targets never come back",
     "file": "bible.html", "matches": 1,
     "find": "    d2r_multiKeep:     ['map', function(){ return multiKeep; }, vaultAfter, multiKeepAbsent],\n",
     "replace": "    d2r_multiKeep:     ['map', function(){ return multiKeep; }, vaultAfter],\n"},
    {"why": "REG-2414 - a first save in another tab is merged against {} (a target it dropped comes back here)",
     "file": "bible.html", "matches": 1,
     "find": "  var n = 0, bv = valOf(base.v);\n",
     "replace": "  var n = 0, bv = (base.v == null) ? (spec.kind === 'set' ? [] : {}) : base.v;\n"},
    {"why": "REG-2414 - a vault store another tab removed stays quarantined here",
     "file": "bible.html", "matches": 1,
     "find": "        && (theirs.v == null || (typeof spec.readable === 'function' && spec.readable(theirs.v)))){\n",
     "replace": "        && ((typeof spec.readable === 'function' && spec.readable(theirs.v)))){\n"},
    {"why": "REG-2414 - the Chronicle loses its absent value: a removal reads as no runeword forged",
     "file": "bible.html", "matches": 1,
     "find": "    d2r_rwMade:        ['map', function(){ return rwMade; }, null, rwMadeAbsent],\n",
     "replace": "    d2r_rwMade:        ['map', function(){ return rwMade; }],\n"},
    {"why": "REG-2414 - the 'same' check reads a removal as {} and writes the default back over the erase",
     "file": "bible.html", "matches": 1,
     "find": "  if (!same(live, tv))\n",
     "replace": "  if (!same(live, theirs.v))\n"},
    {"why": "REG-2414 - the roster registers no absent value (its default lockers)",
     "file": "bible.html", "matches": 1,
     "find": "                             absent: function(){ return DEFAULT_ROSTER.map(function(m){ return Object.assign({}, m); }); },\n",
     "replace": ""},
    {"why": "REG-2414 - the fresh-profile flag is not asked again: a fresh Chronicle reads as the owner's seed",
     "file": "bible.html", "matches": 1,
     "find": "    try { fresh = (window.LSR.getItem('d2r_rwProfile') === 'fresh'); } catch (eF) { fresh = false; }\n",
     "replace": "    fresh = false;\n"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
