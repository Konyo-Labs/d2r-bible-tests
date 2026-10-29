# -*- coding: utf-8 -*-
"""#152 item 2 (REG-2411) — A MULE STORE OF THE WRONG SHAPE NEVER STOPS THE VAULT, AND A VAULT STANDING ON A
QUARANTINED STORE IS HELD, NOT RUN ON A GUESS.

GrokBot's sweep (#230, 10-21, cov*.py), retested unchanged on v3784: d2r_muleRoster saved as {} parses, so the mule
store's load() (which only caught a parse failure) handed it on, `roster.find` threw on the next migration, and the
vault script stopped before renderVault and vaultHandAdd existed - on every reload, for good.

And a page that SURVIVES a quarantined store is the next danger: with d2r_owned or the roster replaced by the page's
default in memory, the render prune drops every filing "whose name left the pool" or "whose mule is not on the roster",
the next saveA() writes that over his mule map, and a records persist writes an empty vault over the last good records.

THE FIX, driven here on the SHIPPED vault module head (RK/AK, the roster, load(), _guardedSet, ⟦VAULT HOLD⟧ and the
migrations after it, cut by its own anchors) and on every door the hold reaches, in node:
  · _muleShape: a roster that is not a list of mules with ids, or a mule map that is not a map, is marked like a parse
    failure, quarantined at the door (bytes kept aside), and the module runs on the default roster / an empty map;
  · THE HOLD: while d2r_owned, the roster, the mule map or the copy counts is quarantined, saveA() refuses, the render
    prune drops nothing, _vaultRecordsPersist / _vaultRecordsRefresh persist nothing (and mark nothing dirty),
    persistOwned does not call a refused write a write, + Add an item refuses in words, and the population line says
    owned UNKNOWN instead of 0;
  · the frame doors (vaultIntake, tvVaultRegister, tvVaultAutoIntake share _vaultIntakeGate) read nothing in while held;
  · a reset pressed while the vault is held says "could not clear" for each part the door kept;
  · "Start it fresh" on the roster keeps one mule for every mule id his map still names. [[unknown-stays-unknown]]
RED_PROOF below; prove with `HEART2_PROVE_WORKERS=1 python3 tv/heart2.py --prove test_a_wrong_shaped_mule_store_never_stops_the_vault`.
"""
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

DEFAULT_IDS = ["sets-major", "sets-rest", "uni-weap", "uni-armor", "uni-small", "runewords", "bases", "magic-rare",
               "charms", "shared", "dupes", "wip"]   # REG-2895 - the CHARMS core locker (his 2026-10-28 ruling)
HELD_OWNED = "the vault is held - d2r_owned will not parse"


def _module(boot_first=False):
    """the vault module's head + saveA/saveR in one scope, its handles on window.__V; optionally the main boot first."""
    s = D.src()
    head = ("var _vaultRecordsRefresh = function(){ OUT.refreshed = (OUT.refreshed || 0) + 1; };\n"
            "(function(){\n" + D.vault_head(s) + "\n" + D.fn(s, "saveR") + "\n" + D.fn(s, "saveA") + "\n"
            "window.__V = { saveA: saveA, saveR: saveR, roster: function(){ return roster; },"
            " assign: function(){ return assign; } };\n})();\n")
    return D.stage(s) + (D.boot(s) if boot_first else "") + head


def _q(o):
    return {k: why for k, why in (o.get("q") or [])}


QREAD = "OUT.q = window.LSR.quarantined().map(function(e){ return [e.key, e.reason]; });"


@unittest.skipIf(D.NODE is None, "node is absent - this law runs the SHIPPED vault module; UNMEASURED, not passing")
class AWrongShapedMuleStoreNeverStopsTheVault(unittest.TestCase):

    def test_a_roster_that_parses_to_the_wrong_shape_does_not_stop_the_script(self):
        for bad in ("{}", '[{"id":"uni-armor","name":"UNI-ARMOR"},null]', '[{"name":"no id"}]', '"text"'):
            o = D.page(_module(), QREAD + "OUT.ids = window.__V.roster().map(function(m){ return m.id; });"
                       "OUT.unread = window._muleStoreUnread('d2r_muleRoster'); OUT.raw = RAW['d2r_muleRoster'];"
                       "OUT.kept = aside(); OUT.defined = typeof window._vaultEnsureSharedLocker;",
                       seed={"d2r_muleRoster": bad})
            self.assertEqual(o["ids"], DEFAULT_IDS, "%s: the module must run on the default roster: %r" % (bad, o))
            self.assertEqual(o["defined"], "function", "%s: the module stopped before its exports" % bad)
            self.assertEqual(o["unread"], "is not a list of mules", bad)
            self.assertEqual(_q(o).get("d2r_muleRoster"), "is not a list of mules", o)
            self.assertEqual(o["raw"], bad, "%s: the migrations wrote over the roster that would not read" % bad)
            self.assertEqual(list(o["kept"].values()), [bad], "the roster's bytes must be kept aside")

    def test_a_mule_map_of_the_wrong_shape_is_quarantined_and_never_written(self):
        for bad in ('"text"', "[1,2]"):
            o = D.page(_module(), QREAD + "var a = window.__V.assign(); OUT.empty = Object.keys(a).length;"
                       "a.Shako = 'uni-armor'; OUT.save = window.__V.saveA(); OUT.raw = RAW['d2r_muleAssign'];",
                       seed={"d2r_muleAssign": bad})
            self.assertEqual(o["empty"], 0)
            self.assertEqual(_q(o).get("d2r_muleAssign"), "is not a map of names to mules", o)
            self.assertFalse(o["save"], "saveA wrote over a mule map that would not read")
            self.assertEqual(o["raw"], bad)

    def test_the_map_is_not_written_while_owned_is_held(self):
        o = D.page(_module(boot_first=True),
                   "var a = window.__V.assign(); a.Shako = 'uni-armor';"
                   "OUT.basis = window._vaultBasisHeld(); OUT.save = window.__V.saveA(); OUT.raw = RAW['d2r_muleAssign'];",
                   seed={"d2r_owned": "{not json", "d2r_muleAssign": '{"Grief":"uni-weap"}'})
        self.assertEqual(o["basis"], HELD_OWNED)
        self.assertFalse(o["save"], "the mule map was written while what it is judged against was quarantined")
        self.assertEqual(o["raw"], '{"Grief":"uni-weap"}')
        self.assertNotIn("refreshed", o, "a refused save must not refresh the records")
        o = D.page(_module(boot_first=True),
                   "var a = window.__V.assign(); a.Shako = 'uni-armor';"
                   "OUT.basis = window._vaultBasisHeld(); OUT.save = window.__V.saveA(); OUT.raw = RAW['d2r_muleAssign'];",
                   seed={"d2r_owned": '["Grief","Harlequin Crest (Shako)"]', "d2r_muleAssign": '{"Grief":"uni-weap"}'})
        self.assertIsNone(o["basis"], "PREMISE: a healthy vault is not held")
        self.assertTrue(o["save"])
        self.assertEqual(o["refreshed"], 1)

    def test_start_it_fresh_keeps_every_mule_the_map_names(self):
        o = D.page(_module(), "OUT.ids = window._vaultRosterFresh().map(function(m){ return m.id; });"
                   "OUT.added = window._vaultRosterFresh().filter(function(m){ return m.added; }).length;",
                   seed={"d2r_muleRoster": "{}", "d2r_muleAssign":
                         '{"Grief":"m1abcdef","Enigma":"war1","Torch":"__keep","Junk":"__throwout","Shako":"uni-armor"}'})
        # names in order (Enigma -> war1, Grief -> m1abcdef); a default id and the __ sentinels are never added
        self.assertEqual(o["ids"], DEFAULT_IDS + ["war1", "m1abcdef"],
                         "every mule his map names must survive a fresh roster (and no sentinel becomes a mule)")
        self.assertEqual(o["added"], 2)

    def test_the_render_prune_drops_nothing_while_held(self):
        s = D.src()
        prune = D.between(s, "    var _pruneHeld = ", "    // v360 — shared-stash items", keep_b=False)
        body = ("var assign = { A: 'uni-armor', B: 'gone-mule', C: 'uni-armor' }, pool = ['A'], poolAll = pool, _pvW6 = {};"
                "function muleById(id){ return id === 'uni-armor' ? { id: id } : null; }"
                "window._vaultBasisHeld = function(){ return HELD; };"
                "var HELD = %s;\n" + prune + "\nOUT.left = Object.keys(assign).sort();")
        held = D.page("", body % '"the vault is held - d2r_owned will not parse"')
        self.assertEqual(held["left"], ["A", "B", "C"], "the prune dropped filings against a quarantined store")
        free = D.page("", body % "null")
        self.assertEqual(free["left"], ["A"], "PREMISE: unheld, the prune drops the unknown mule and the unwitnessed name")

    def test_records_are_not_persisted_or_marked_dirty_from_a_held_basis(self):
        s = D.src()
        pieces = ("var CALLS = []; var _vrRecHold = 0;"
                  "function _vaultRecords(){ CALLS.push('derive'); return { ok: false }; }"
                  "function _vrRecMarkDirty(){ CALLS.push('dirty'); }"
                  "function _vaultRecordsStampOk(){ return true; } function _vrRecSigSame(){ return false; }\n"
                  + D.fn(s, "_vaultRecordsPersist") + "\n" + D.fn(s, "_vaultRecordsRefresh") + "\n")
        o = D.page(pieces, "window._vaultBasisHeld = function(){ return '%s'; };"
                   "OUT.p = _vaultRecordsPersist(); OUT.r = _vaultRecordsRefresh(); OUT.calls = CALLS;" % HELD_OWNED)
        self.assertEqual((o["p"]["wrote"], o["p"].get("held")), (False, True), o)
        self.assertIn("d2r_owned will not parse", o["p"]["why"])
        self.assertTrue(o["r"].get("held"), o)
        self.assertEqual(o["calls"], [], "a held basis must derive nothing and mark nothing dirty (the stored records "
                                         "stay the last good model): %r" % o["calls"])
        o = D.page(pieces, "OUT.p = _vaultRecordsPersist(); OUT.calls = CALLS;")
        self.assertEqual(o["calls"], ["derive"], "PREMISE: unheld, the persist derives the model")

    def test_the_hand_door_refuses_in_words_while_held(self):
        s = D.src()
        pieces = ("var CALLS = []; function _vhResolve(raw){ CALLS.push(raw); return { ok: true, name: raw }; }"
                  "function _vaultKeeps(){ return true; } function _vhAlias(){ return null; }"
                  "function _vaultHandBase(){ return null; }\n" + D.fn(s, "_vhTwinAsk") + "\n"   # REG-3075 the door's one question
                  + D.fn(s, "_vhPrepare") + "\n")
        o = D.page(pieces, "window._vaultHeld = function(){ return { keys: ['d2r_owned'], why: '%s' }; };"
                   "OUT.r = _vhPrepare('Harlequin Crest', null, {}); OUT.calls = CALLS;" % HELD_OWNED)
        self.assertFalse(o["r"]["ok"])
        self.assertEqual(o["r"]["refused"], "held")
        self.assertIn("d2r_owned will not parse", o["r"]["why"])
        self.assertIn("nothing was added", o["r"]["why"])
        self.assertEqual(o["calls"], [], "a held vault must refuse before anything is asked or touched")
        o = D.page(pieces, "OUT.r = _vhPrepare('Harlequin Crest', null, {}); OUT.calls = CALLS;")
        self.assertTrue(o["r"]["ok"], "PREMISE: unheld, the door goes on")

    def test_the_frame_doors_read_nothing_in_while_held(self):
        s = D.src()
        pieces = "window._vaultFrameRefuse = function(){ return null; };\n" + D.fn(s, "_vaultIntakeGate") + "\n"
        o = D.page(pieces, "window._vaultHeld = function(){ return { keys: ['d2r_owned'], why: '%s' }; };"
                   "OUT.r = _vaultIntakeGate();" % HELD_OWNED)
        self.assertEqual((o["r"]["refused"], o["r"]["registered"]), ("held", False), o)
        self.assertIn("d2r_owned will not parse", o["r"]["why"])
        o = D.page(pieces, "OUT.r = _vaultIntakeGate();")
        self.assertIsNone(o["r"], "PREMISE: an unheld vault with AUTO INTAKE on lets a frame through")

    def test_persist_owned_does_not_call_a_refused_write_a_write(self):
        s = D.src()
        pieces = (D.stage(s) + "var owned = new Set(['Grief']), magicFinds = {}, unknownReads = new Set(), copies = {},"
                  " multiKeep = {}, REFRESH = 0; function _vaultRecordsRefresh(){ REFRESH++; }\n"
                  + D.fn(s, "persistOwned") + "\n")
        o = D.page(pieces, "window.LSR.quarantine('d2r_owned', 'will not parse'); persistOwned();"
                   "OUT.refresh = REFRESH; OUT.raw = RAW['d2r_owned'];", seed={"d2r_owned": "{bad"})
        self.assertEqual(o["raw"], "{bad")
        self.assertEqual(o["refresh"], 0, "a refused d2r_owned write must not refresh the records from memory")
        o = D.page(pieces, "persistOwned(); OUT.refresh = REFRESH; OUT.raw = RAW['d2r_owned'];")
        self.assertEqual((o["refresh"], o["raw"]), (1, '["Grief"]'), "PREMISE: a landed write refreshes")

    def test_a_reset_pressed_while_held_says_it_could_not_clear(self):
        s = D.src()
        pieces = (D.stage(s) + "var AK = 'd2r_muleAssign', _vrRecHold = 0; var owned = new Set(['A']);"
                  "function persistOwned(){ window.LSR.setItem('d2r_owned', JSON.stringify(Array.from(owned))); }"
                  "var _VAULT_RESET_SCOPE = { clears: {"
                  "  owned: { store: 'd2r_owned', clear: function(){ owned.clear(); persistOwned(); } },"
                  "  assign: { store: 'd2r_muleAssign', clear: function(){ window.LSR.setItem('d2r_muleAssign', '{}'); } } },"
                  " doors: { vaultClearHistory: ['assign', 'owned'] } };"
                  "function _vKeepsFor(){ return []; } function _vResetRead(k){ return window.LSR.getItem(k); }"
                  "function _vResetCount(v){ return v ? 1 : 0; } function _vaultRecordedFilings(){ return {}; }"
                  "function _vaultRecordsRefresh(){} async function _vaultRefileFromPlan(R){ R.rebuilt = []; }"
                  "function _vaultResetPersist(){}\n" + D.fn(s, "_vaultResetRun") + "\n")
        body = ("window.__ASYNC = true; %s"
                "_vaultResetRun('vaultClearHistory').then(function(R){ OUT.failed = R.failed.slice().sort(); OUT.ok = R.ok;"
                " OUT.raw = RAW['d2r_owned']; done(); });")
        held = D.page(pieces, body % ("window.LSR.quarantine('d2r_owned', 'will not parse');"
                                      "window._vaultBasisHeld = function(){ return '%s'; };" % HELD_OWNED),
                      seed={"d2r_owned": "{bad", "d2r_muleAssign": '{"Grief":"uni-weap"}'})
        self.assertEqual(held["failed"], ["assign", "owned"],
                         "a reset over a held vault must say what it could not clear: %r" % held)
        self.assertFalse(held["ok"])
        self.assertEqual(held["raw"], "{bad", "the quarantined store must survive a reset")
        free = D.page(pieces, body % "", seed={"d2r_owned": '["A"]', "d2r_muleAssign": '{"Grief":"uni-weap"}'})
        self.assertEqual((free["failed"], free["ok"]), ([], True), "PREMISE: an unheld reset is clean: %r" % free)

    def test_the_population_line_says_unknown_not_zero(self):
        s = D.src()
        pieces = D.window_fn(s, "_vaultPopHtml") + "\n"
        o = D.page(pieces, "OUT.held = window._vaultPopHtml({ owned: null, heldWhy: '%s' });"
                   "OUT.free = window._vaultPopHtml({ owned: 3, shared: 0, filed: 3, carried: 0, loose: 0, sp: 0, orphans: 0 });"
                   % HELD_OWNED)
        self.assertIn("owned <b>UNKNOWN</b>", o["held"])
        self.assertIn("d2r_owned will not parse", o["held"])
        self.assertNotIn("<b>0</b> owned", o["held"], "a held vault must never read as an empty one")
        self.assertIn("<b>3</b> owned", o["free"], "PREMISE: an unheld line still counts")
        render = D.fn(s, "renderVaultDraw")
        i = render.find("_popHeld")
        j = render.find("_pEl.innerHTML", i)
        self.assertTrue(0 < i < j, "renderVaultDraw no longer asks whether the vault is held before it paints the line")
        self.assertIn("_sub76.owned = null", render[i:j], "a held vault's line must be built with owned UNKNOWN")


RED_PROOF = [
    {"why": "REG-2411 - a roster that parses to the wrong shape reaches roster.find again (the vault script stopped)",
     "file": "bible.html", "matches": 1,
     "find": "  function _muleShapeWhy(k, v){\n",
     "replace": "  function _muleShapeWhy(k, v){\n    if (k === RK) return null;\n"},
    {"why": "REG-2411 - saveA writes the mule map while d2r_owned / the roster is quarantined",
     "file": "bible.html", "matches": 1,
     "find": "    if (k === AK && typeof window._vaultBasisHeld === 'function' && window._vaultBasisHeld()) {\n",
     "replace": "    if (false) {\n"},
    {"why": "REG-2411 - the render prune drops filings against a quarantined store's default",
     "file": "bible.html", "matches": 1,
     "find": "      if (_pruneHeld) return;\n",
     "replace": ""},
    {"why": "REG-2411 - the records persist writes a model derived from a quarantined store",
     "file": "bible.html", "matches": 1,
     "find": "    if (_basis) return { ok: false, wrote: false, unknown: true, held: true, why: _basis + ' - nothing persisted' };\n",
     "replace": ""},
    {"why": "REG-2411 - the records refresh runs (and marks dirty) on a held basis",
     "file": "bible.html", "matches": 1,
     "find": "    if (_basisR) return { ok: false, held: true, why: _basisR };\n",
     "replace": ""},
    {"why": "REG-2411 - + Add an item goes on while the vault is held (it said 'is yours' and nothing was saved)",
     "file": "bible.html", "matches": 1,
     "find": "    if (_hold) return { ok: false, refused: 'held', held: _hold.keys,\n",
     "replace": "    if (false) return { ok: false, refused: 'held', held: _hold.keys,\n"},
    {"why": "REG-2411 - persistOwned calls a refused d2r_owned write a write and refreshes the records from memory",
     "file": "bible.html", "matches": 1,
     "find": "    try { _ownedOk = (window.LSR.setItem('d2r_owned', JSON.stringify(Array.from(owned))) !== false); } catch(e){}\n",
     "replace": "    try { window.LSR.setItem('d2r_owned', JSON.stringify(Array.from(owned))); _ownedOk = true; } catch(e){}\n"},
    {"why": "REG-2411 - the population line counts a held vault as 0 owned",
     "file": "bible.html", "matches": 1,
     "find": "    if (p.owned === null)\n",
     "replace": "    if (false)\n"},
    {"why": "REG-2411 - a frame reads an item into a held vault (the write is refused and the frame is marked read)",
     "file": "bible.html", "matches": 1,
     "find": "    if (_heldV) return { ok: false, refused: 'held', registered: false, held: _heldV.keys,\n",
     "replace": "    if (false) return { ok: false, refused: 'held', registered: false, held: _heldV.keys,\n"},
    {"why": "REG-2411 - a reset over a held vault says it cleared what the door kept",
     "file": "bible.html", "matches": 1,
     "find": "      if (held) R.failed.push(p);\n",
     "replace": ""},
    {"why": "REG-2411 - a fresh roster drops the mules his map still names (their filings would be pruned)",
     "file": "bible.html", "matches": 1,
     "find": "      if (typeof id !== 'string' || !id || id.indexOf('__') === 0 || have[id]) return;\n",
     "replace": "      return;\n"},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
