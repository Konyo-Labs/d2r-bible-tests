# -*- coding: utf-8 -*-
"""REG-2415 (review of REG-2410, r1 reproduced) — A WITNESS STORE THAT WILL NOT READ IS QUARANTINED AND HOLDS THE VAULT.

d2r_vaultProv holds a witness row beside every mule filing ("from what picture is this here?"). The vault module read
it through `JSON.parse(raw || '{}')` with `catch -> {}`: bytes cut short mid-write, or a store that parsed to a list,
read as an EMPTY store. vaultFile refused an unreadable store only inside `if (hand)`; the reader / frame / sorter /
rebuild / restore / move paths did `var pa = _provAll(); pa[nm] = row; _provWrite(pa);` - so ONE frame filing wrote
{its own row} over every row he had (the review drove it: Grief's and Shako's rows gone, ok:true mode:'filed'), the
W6 render prune read every filing as unwitnessed, nothing was quarantined, kept aside or said, and the vault was not
held because the store was not in VAULT_BASIS.

THE FIX, driven here on the SHIPPED code (the store door window.LSR, the boot and its notice, ⟦TAB SYNC⟧, the vault
module's head and its whole ⟦#246 VAULTFILE⟧ block, the W6 prune, the removal journal and its doors, the sorter, the
socket fix, the mule delete and the owned door's reader - each cut from bible.html, never re-typed), in node:
  · bytes that will not parse, or are not a map, are UNKNOWN (null) and QUARANTINED at the door as the module loads:
    kept aside byte for byte, every write refused, the notice names the store in his words;
  · the store is in VAULT_BASIS, so the vault is HELD: the mule map is not written and the prune drops nothing;
  · every branch of the one filing door refuses in words, and so do the removal, the TV unvault, the sorter, the
    socket fix and the mule delete - nothing is written over the bytes and no filing moves;
  · the drop / demote / unlock helpers write nothing over it, a bare write of UNKNOWN is refused, and a write the door
    refuses is never read back as saved;
  · the tile, the evidence line and the evidence panel say UNKNOWN, never "NO WITNESS" or "No provenance";
  · the owned door's own reader quarantines the same key; another tab's store that reads lifts the hold;
  · nothing saved yet is a measured nothing ({}), and the door files on it as before.
The browser half (the notice painted on the board) is tests/reg2410_stores_never_bricked.spec.ts on CI.
RED_PROOF below; prove with `HEART2_PROVE_WORKERS=1 python3 tv/heart2.py --prove test_a_witness_store_that_will_not_read_holds_the_vault`.
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

PROV = "d2r_vaultProv"
#: his witness store, cut short mid-write (the review's r1): Grief's row whole, Shako's half-written
CORRUPT = ('{"Grief":{"mule":"uni-weap","source":"hand","by":"hand","at":"2026-10-01","where":"the vault manager"},'
           '"Shako":{"mule":"uni-armor","source":"stash","looks":[{"id":"s1","frame":"f9","conf":0.93}')
GOOD_ROW = '{"mule":"uni-weap","holder":"UNI-WEAPONS","source":"hand","by":"hand","at":"2026-10-01","where":"the vault manager","sessions":[],"looks":[]}'
L2 = "[{session:'s_a',frame:'f_a.jpg',conf:0.9},{session:'s_b',frame:'f_b.jpg',conf:0.85}]"
HAND = "{ by: 'hand', at: '2026-10-22T10:00:00Z', where: 'the vault manager' }"


def _seed(prov=CORRUPT, **more):
    out = {"d2r_owned": '["Grief","Enigma","Harlequin Crest (Shako)"]', "d2r_muleAssign": '{"Grief":"uni-weap"}'}
    if prov is not None:
        out[PROV] = prov
    out.update(more)
    return out


def _async_window_fn(s, name):
    """`window.NAME = async function(...){...};` brace-matched. -> str"""
    start = "  window.%s = async function(" % name
    if s.count(start) != 1:
        raise AssertionError("%r matched %d times - the anchor moved" % (start, s.count(start)))
    return D.start_to_close(s, s.index(start), name) + ";"


def _pieces(s):
    """the vault page, with the module's own helpers exposed and the doors outside the filing block cut in"""
    expose = ("window.__V = { provAll: _provAll, provWrite: _provWrite, provDrop: _provDrop, provDemote: _provDemote,"
              " hardUnlock: _hardUnlock, receiptWitness: _receiptStashWitness, assign: function(){ return assign; },"
              " saveA: saveA, roster: function(){ return roster; } };\n"
              "window.__prune = function(pool){ var poolAll = pool;\n" + D.between(s, "    var _pvLive = _provAll();\n", "    // v360 — shared-stash items",
                                                               keep_b=False) + "\n};\n"
              + "var _VR_LOG = 'd2r_vaultRemoved', _VR_RING = 20;\n"
              + D.between(s, "  function _vrRead(){", "  /* the heart and the console read the journal through here", keep_b=False)
              + D.between(s, "  window.vaultRemove = function(names, opts){", "  /* The reverse of exactly one batch", keep_b=False)
              + D.fn(s, "_tvFrameMs") + "\n" + D.window_fn(s, "tvVaultUnregisterMany") + "\n"
              + D.window_fn(s, "vaultAutoAssign") + "\n" + D.window_fn(s, "vaultFixSockets") + "\n"
              + D.fn(s, "_vmAddedMule") + "\n" + _async_window_fn(s, "vaultDeleteMule") + "\n")
    owned_door = ("(function(){ var KEY = 'd2r_vaultProv';\n"
                  + D.between(s, "  function _readQ(why){", "  function _write(all){", keep_b=False)
                  + "window.__ownedRead = _read; })();\n")
    return D.vault_page(s, expose) + "window.uiConfirm = function(){ return Promise.resolve(true); };\n" + owned_door


OTHER = ("function other(k, nv){ var ov = RAW[k] == null ? null : RAW[k]; if (nv == null) delete RAW[k]; else RAW[k] = String(nv);"
         " fire(k, ov, nv == null ? null : String(nv)); }\n")
WRITES = ("var WROTE = []; var _set = window.LSR.setItem; window.LSR.setItem = function(k, v){ WROTE.push(k);"
          " return _set.call(window.LSR, k, v); };\n")


def _run(body, seed):
    s = D.src()
    return D.page(_pieces(s), OTHER + WRITES + body, seed=seed)


@unittest.skipIf(D.NODE is None, "node is absent - this law runs the SHIPPED vault module; UNMEASURED, not passing")
class AWitnessStoreThatWillNotReadHoldsTheVault(unittest.TestCase):

    def test_bytes_that_will_not_parse_are_quarantined_as_the_module_loads_never_read_as_empty(self):
        o = _run("var q = window.LSR.quarantined('d2r_vaultProv'); OUT.q = q ? { kind: q.kind, reason: q.reason, asideOk: q.asideOk } : null;"
                 "OUT.read = window.__V.provAll(); OUT.aside = aside();"
                 "OUT.notice = (document.getElementById('store-quarantine') || {}).innerHTML || '';", _seed())
        self.assertEqual(o["q"], {"kind": "quarantine", "reason": "will not parse", "asideOk": True},
                         "the witness store must be quarantined when the module loads, before anything files against it")
        self.assertIsNone(o["read"], "bytes that will not parse were read as a witness store")
        self.assertEqual(list(o["aside"].values()), [CORRUPT], "the exact bytes must be kept aside")
        self.assertIn('data-store="d2r_vaultProv"', o["notice"])
        self.assertIn("the vault witness rows", o["notice"], "the notice must say what the store is, in his words")

    def test_a_reader_filing_over_it_is_refused_and_every_row_stays(self):
        """The review's r1: a frame / reader witness, two looks, for a name not filed yet."""
        o = _run("WROTE.length = 0; OUT.r = window.vaultFile('Enigma', { by: 'reader', lane: 'stash', sessions: " + L2 + " });"
                 "OUT.raw = RAW['d2r_vaultProv']; OUT.assign = JSON.parse(JSON.stringify(window.__V.assign()));"
                 "OUT.map = RAW['d2r_muleAssign']; OUT.wrote = WROTE.slice();", _seed())
        self.assertFalse(o["r"]["ok"], o["r"])
        self.assertEqual(o["r"]["refused"], "prov-unreadable")
        self.assertIn("d2r_vaultProv", o["r"]["why"], "the refusal must name the store")
        self.assertEqual(o["raw"], CORRUPT, "a filing wrote over the witness rows it could not read")
        self.assertEqual(o["assign"], {"Grief": "uni-weap"}, "a filing landed in the mule map with no witness row")
        self.assertEqual(o["map"], '{"Grief":"uni-weap"}')
        self.assertEqual(o["wrote"], [], "nothing is even tried")

    def test_every_branch_of_the_one_door_refuses(self):
        o = _run("OUT.hand = window.vaultFile('Enigma', " + HAND + ", { mule: 'uni-armor' }).refused;"
                 "OUT.move = window.vaultFile('Grief', null, { move: true, mule: 'uni-armor', by: 'vault audit' }).refused;"
                 "OUT.restore = window.vaultFile('Enigma', null, { restore: true, mule: 'uni-armor', prov: { source: 'hand', by: 'hand' } }).refused;"
                 "OUT.rebuild = window.vaultFile('Enigma', { sessions: " + L2 + " }, { rebuild: true, mule: 'uni-armor',"
                 " plan: { name: 'Enigma', tier: 'PROVEN', why: 'PROVEN', successes: 2, trials: 2 } }).refused;"
                 "OUT.raw = RAW['d2r_vaultProv']; OUT.assign = JSON.parse(JSON.stringify(window.__V.assign()));", _seed())
        for branch in ("hand", "move", "restore", "rebuild"):
            self.assertEqual(o[branch], "prov-unreadable", "the %s branch filed over an unreadable witness store" % branch)
        self.assertEqual(o["raw"], CORRUPT)
        self.assertEqual(o["assign"], {"Grief": "uni-weap"}, "a branch moved or filed an item with its witness UNKNOWN")

    def test_a_store_of_the_wrong_shape_is_unknown_too(self):
        for raw, held in (("[]", "a list"), ("null", "null"), ('"text"', "string")):
            o = _run("var q = window.LSR.quarantined('d2r_vaultProv'); OUT.reason = q && q.reason; OUT.read = window.__V.provAll();",
                     _seed(raw))
            self.assertIsNone(o["read"], "%s was read as a witness store" % raw)
            self.assertEqual(o["reason"], "is not a map of witness rows (it holds %s)" % held)

    def test_nothing_saved_yet_is_a_measured_nothing_and_the_door_files_on_it(self):
        o = _run("OUT.read = window.__V.provAll(); OUT.q = window.LSR.quarantined('d2r_vaultProv');"
                 "OUT.r = window.vaultFile('Enigma', " + HAND + ", { mule: 'uni-armor' });"
                 "OUT.row = JSON.parse(RAW['d2r_vaultProv']).Enigma; OUT.assign = JSON.parse(JSON.stringify(window.__V.assign()));",
                 _seed(None))
        self.assertEqual(o["read"], {}, "a store never saved is an empty one, not UNKNOWN")
        self.assertIsNone(o["q"])
        self.assertTrue(o["r"]["ok"], o["r"])
        self.assertEqual(o["row"]["source"], "hand")
        self.assertEqual(o["assign"]["Enigma"], "uni-armor")

    def test_the_witness_store_holds_the_vault(self):
        o = _run("OUT.held = window._vaultBasisHeld(); window.__V.assign().Enigma = 'uni-armor';"
                 "OUT.save = window.__V.saveA(); OUT.map = RAW['d2r_muleAssign'];", _seed())
        self.assertIn("d2r_vaultProv", o["held"] or "", "the vault stands on the witness rows, so it must be held")
        self.assertFalse(o["save"], "the mule map was written while the rows it stands on would not read")
        self.assertEqual(o["map"], '{"Grief":"uni-weap"}')

    def test_the_render_prune_drops_nothing_while_the_store_will_not_read(self):
        """Isolated from the basis hold: the prune's own guard. With a store that reads, the same filing is pruned."""
        body = ("window._vaultBasisHeld = function(){ return null; }; window.__V.assign()['Old Ring'] = 'uni-armor';"
                "window.__prune(['Grief']); OUT.left = Object.keys(window.__V.assign()).sort();")
        bad = _run(body, _seed())
        good = _run(body, _seed("{}"))
        self.assertEqual(bad["left"], ["Grief", "Old Ring"], "the prune dropped a filing against witness rows it could not read")
        self.assertEqual(good["left"], ["Grief"], "the prune must still drop an unwitnessed filing that left the pool")

    def test_drop_demote_unlock_and_a_bare_write_put_nothing_over_it(self):
        o = _run("OUT.drop = window.__V.provDrop(['Grief']); OUT.demote = window.__V.provDemote('Grief');"
                 "OUT.unlock = window.__V.hardUnlock('Grief', 'test'); OUT.bare = window.__V.provWrite(null);"
                 "OUT.raw = RAW['d2r_vaultProv'];", _seed())
        self.assertEqual((o["drop"], o["demote"], o["unlock"], o["bare"]), (0, False, False, False))
        self.assertEqual(o["raw"], CORRUPT)
        o = _run("OUT.bare = window.__V.provWrite(null); OUT.has = Object.prototype.hasOwnProperty.call(RAW, 'd2r_vaultProv');",
                 _seed(None))
        self.assertFalse(o["bare"])
        self.assertFalse(o["has"], "UNKNOWN was written as a witness store")

    def test_a_write_the_door_refuses_is_never_read_back_as_saved(self):
        """A store that reads, held at the door (another tab's clear): the rows a caller put in are not 'saved'."""
        locked = '{"Grief":{"mule":"uni-weap","source":"stash","locked":true,"tier":"HARDENED","looks":[]}}'
        o = _run("window.LSR.hold('d2r_vaultProv', 'another tab cleared this browser’s saved data');"
                 "var pa = window.__V.provAll(); pa.X = { mule: 'uni-armor', source: 'hand' }; OUT.w = window.__V.provWrite(pa);"
                 "OUT.x = Object.prototype.hasOwnProperty.call(window.__V.provAll(), 'X');"
                 "OUT.unlock = window.__V.hardUnlock('Grief', 'test'); OUT.locked = window.__V.provAll().Grief.locked;"
                 "OUT.raw = RAW['d2r_vaultProv'];", _seed(locked))
        self.assertFalse(o["w"], "a write the door refused answered as saved")
        self.assertFalse(o["x"], "a row the door refused was read back as saved")
        self.assertFalse(o["unlock"], "a release the door refused answered as released")
        self.assertTrue(o["locked"])
        self.assertEqual(o["raw"], locked)

    def test_the_tile_and_the_evidence_say_unknown(self):
        o = _run("OUT.say = window._vaultProvSay('Grief'); OUT.line = window._vaultEvidenceLine('Grief');"
                 "var m = window._vaultEvidenceOf('Grief'); OUT.unknown = !!m.unknown;"
                 "OUT.html = window._vaultEvidenceHtml(m, null);"
                 "OUT.gathered = window.__V.receiptWitness('Grief', { lane: 'stash', sessions: " + L2 + " });", _seed())
        self.assertIn("UNKNOWN", o["say"], "the tile must say the witness is UNKNOWN, never NO WITNESS")
        self.assertIn("UNKNOWN", o["line"])
        self.assertTrue(o["unknown"])
        self.assertIn("would not read", o["html"])
        self.assertNotIn("No provenance", o["html"], "the panel said nothing was recorded over rows it could not read")
        self.assertIsNone(o["gathered"], "a witness was gathered from rows that could not be read")

    def test_the_owned_doors_own_reader_quarantines_it_too(self):
        s = D.src()
        pieces = (D.stage(s) + D.boot(s) + "(function(){ var KEY = 'd2r_vaultProv';\n"
                  + D.between(s, "  function _readQ(why){", "  function _write(all){", keep_b=False)
                  + "window.__ownedRead = _read; })();\n")
        o = D.page(pieces, "OUT.read = window.__ownedRead(); var q = window.LSR.quarantined('d2r_vaultProv');"
                           "OUT.reason = q && q.reason; OUT.aside = Object.keys(aside()).length;", seed=_seed())
        self.assertIsNone(o["read"])
        self.assertEqual(o["reason"], "will not parse", "the owned door met the bad bytes and did not name them")
        self.assertEqual(o["aside"], 1)

    def test_another_tab_writing_a_store_that_reads_lifts_the_hold(self):
        o = _run("other('d2r_vaultProv', '{\"Grief\":" + GOOD_ROW.replace('"', '\\"') + "}');"
                 "OUT.q = window.LSR.quarantined('d2r_vaultProv'); OUT.held = window._vaultBasisHeld();"
                 "OUT.rows = Object.keys(window.__V.provAll() || {});"
                 "OUT.r = window.vaultFile('Enigma', " + HAND + ", { mule: 'uni-armor' }).ok;", _seed())
        self.assertIsNone(o["q"], "another tab's store that reads must lift the quarantine here")
        self.assertIsNone(o["held"])
        self.assertEqual(o["rows"], ["Grief"])
        self.assertTrue(o["r"], "once the rows read, the door files again")

    def test_the_removal_the_unvault_the_sorter_the_rename_and_the_mule_delete_refuse_in_words(self):
        o = _run("window.__ASYNC = true;"
                 "var rm = window.vaultRemove(['Grief']); OUT.rm = { refused: rm.refused, removed: rm.removed };"
                 "OUT.keep = window.vaultRemove(['Enigma'], { keepFiling: true, quiet: true }).removed;"
                 "var tv = window.tvVaultUnregisterMany(['Grief'], null); OUT.tv = { ok: tv.ok, refused: tv.refused };"
                 "OUT.sort = window.vaultAutoAssign().refused;"
                 "window.vaultFixSockets('Grief', 4);"
                 "window.__V.roster().push({ id: 'm1x2y3z4', name: 'MULE7', icon: 'x', note: '', added: true });"
                 "window.vaultDeleteMule('m1x2y3z4').then(function(){"
                 "  OUT.mule = window.__V.roster().some(function(m){ return m.id === 'm1x2y3z4'; });"
                 "  OUT.owned = Array.from(owned).sort(); OUT.assign = JSON.parse(JSON.stringify(window.__V.assign()));"
                 "  OUT.raw = RAW['d2r_vaultProv']; OUT.status = STATUS.slice(); done(); });", _seed())
        self.assertEqual(o["rm"], {"refused": "prov-unreadable", "removed": []}, "a removal took a filing whose row it could not carry")
        self.assertEqual(o["keep"], ["Enigma"], "a removal that keeps the filing touches no row, so it is not held")
        self.assertEqual(o["tv"], {"ok": False, "refused": "prov-unreadable"})
        self.assertEqual(o["sort"], "prov-unreadable")
        self.assertTrue(o["mule"], "a mule was deleted while the rows on it could not be written")
        self.assertIn("Grief", o["owned"], "the TV unvault took the name out of owned with no journal")
        self.assertEqual(o["assign"], {"Grief": "uni-weap"})
        self.assertEqual(o["raw"], CORRUPT)
        said = " | ".join(o["status"])
        for words in ("nothing removed", "nothing was sorted", "the socket fix waits", "MULE7 was not deleted"):
            self.assertIn(words, said, "a refusal was not said: %r" % words)


RED_PROOF = [
    {"why": "REG-2415 - bytes that will not parse are read as an empty witness store again",
     "file": "bible.html", "matches": 1,
     "find": "      if (why) return unk(why);\n",
     "replace": "      if (why) return {};\n"},
    {"why": "REG-2415 - the witness store that will not read is not quarantined (not kept aside, not said)",
     "file": "bible.html", "matches": 1,
     "find": "      try { if (window.LSR && typeof window.LSR.quarantine === 'function') window.LSR.quarantine(PROV_KEY, why); } catch (eQ) {}\n",
     "replace": ""},
    {"why": "REG-2415 - the one filing door files over an UNKNOWN witness store (the review's r1)",
     "file": "bible.html", "matches": 1,
     "find": "    if (_pv0 === null || _pvQ0)\n",
     "replace": "    if (false)\n"},
    {"why": "REG-2415 - the vault does not stand on its witness rows: the map is written while they will not read",
     "file": "bible.html", "matches": 1,
     "find": "d2r_copies: 1, d2r_vaultProv: 1, d2r_magicFinds: 1 });\n",
     "replace": "d2r_copies: 1, d2r_magicFinds: 1 });\n"},
    {"why": "REG-2415 - the render prune reads an UNKNOWN witness store as no rows and drops filings",
     "file": "bible.html", "matches": 1,
     "find": "    var _pvW6 = (_pvLive === null) ? null : {};\n",
     "replace": "    var _pvW6 = {};\n"},
    {"why": "REG-2415 - a bare write of UNKNOWN is written as the witness store",
     "file": "bible.html", "matches": 1,
     "find": "    if (!all || typeof all !== 'object' || Array.isArray(all)) return false;\n    var raw = JSON.stringify(all);\n",
     "replace": "    var raw = JSON.stringify(all);\n"},
    {"why": "REG-2415 - a write the door refused is answered as saved and read back from the cache",
     "file": "bible.html", "matches": 1,
     "find": "    if (window.LSR.setItem(PROV_KEY, raw) === false){\n",
     "replace": "    if (window.LSR.setItem(PROV_KEY, raw) === 'never'){\n"},
    {"why": "REG-2415 - a release the door would refuse answers released",
     "file": "bible.html", "matches": 1,
     "find": "    if (_provHeldNow()) return false;\n",
     "replace": ""},
    {"why": "REG-2415 - the drop helper indexes an UNKNOWN store",
     "file": "bible.html", "matches": 1,
     "find": "    if (!all) return 0;\n    (Array.isArray(names) ? names : [names]).forEach(function(k){\n",
     "replace": "    (Array.isArray(names) ? names : [names]).forEach(function(k){\n"},
    {"why": "REG-2415 - the tile reads an UNKNOWN witness store (and throws, or says NO WITNESS)",
     "file": "bible.html", "matches": 1,
     "find": "    if (_provAll() === null) return 'witness UNKNOWN - the witness store would not read';\n",
     "replace": ""},
    {"why": "REG-2415 - the evidence line says nothing over rows it could not read",
     "file": "bible.html", "matches": 1,
     "find": "    if (_pvEL === null) return 'evidence UNKNOWN - the witness store would not read, so who or what filed this cannot be told';\n",
     "replace": "    if (_pvEL === null) return '';\n"},
    {"why": "REG-2415 - the evidence panel says 'No provenance' over rows it could not read",
     "file": "bible.html", "matches": 1,
     "find": "    if (m.unknown && !m.has){\n",
     "replace": "    if (false){\n"},
    {"why": "REG-2415 - the owned door's reader meets the bad bytes and names nothing",
     "file": "bible.html", "matches": 1,
     "find": "    try { if (window.LSR && typeof window.LSR.quarantine === 'function') window.LSR.quarantine(KEY, why); } catch (eQ) {}\n",
     "replace": ""},
    {"why": "REG-2415 - the witness store is left out of the tab sync: another tab's good store never lifts the hold",
     "file": "bible.html", "matches": 1,
     "find": "    ['d2r_vaultProv', 'd2r_mulePos', 'd2r_muleEquip'].forEach(function(k){\n",
     "replace": "    ['d2r_mulePos', 'd2r_muleEquip'].forEach(function(k){\n"},
    {"why": "REG-2415 - a removal takes filings whose witness rows it cannot carry or drop",
     "file": "bible.html", "matches": 1,
     "find": "    var _whyRm = (!opts.keepFiling && typeof window._vaultProvHeld === 'function') ? window._vaultProvHeld() : null;\n",
     "replace": "    var _whyRm = null;\n"},
    {"why": "REG-2415 - the TV unvault's residue loop takes names out of owned with no journal while the rows will not read",
     "file": "bible.html", "matches": 1,
     "find": "    var _pvTv = (typeof window._vaultProvHeld === 'function') ? window._vaultProvHeld() : null;\n",
     "replace": "    var _pvTv = null;\n"},
    {"why": "REG-2415 - the sorter walks an UNKNOWN witness store",
     "file": "bible.html", "matches": 1,
     "find": "    if (_pvSw){ status('⚠ nothing was sorted - ' + _pvSw); return { filed: 0, refused: 'prov-unreadable', why: _pvSw }; }\n",
     "replace": ""},
    {"why": "REG-2415 - the socket fix fails silently over an UNKNOWN witness store (REG-2521's basis-held wait stands "
            "behind it and asks every basis store, the witness store among them, so both waits are taken: either alone keeps "
            "the fix waiting)",
     "file": "bible.html", "matches": 1,
     "find": "      if (_pvFix){ status('⚠ the socket fix waits - ' + _pvFix); return; }\n      /* REG-2521 fix round (review of REG-2521, major) — AND WHILE ANY STORE THE VAULT STANDS ON IS HELD (owned, the\n         roster, the mule map, the copies, Magic & Rare): vaultFile refuses at its top then, and this click used to drop\n         the old label's filing and its witness row FIRST and ask vaultFile to put them back after - so the row was gone\n         for good, the item unfiled, and the status said \"fixed\". It waits now, in words, before anything is touched.\n         (Inline, not the helper above: a law cuts this door on its own.) */\n      var _bhFix = (typeof window._vaultBasisHeld === 'function') ? window._vaultBasisHeld() : null;\n      if (_bhFix){ status('⚠ the socket fix waits - ' + _bhFix",
     "replace": "      if (false){ status('⚠ the socket fix waits - ' + _pvFix); return; }\n      /* REG-2521 fix round (review of REG-2521, major) — AND WHILE ANY STORE THE VAULT STANDS ON IS HELD (owned, the\n         roster, the mule map, the copies, Magic & Rare): vaultFile refuses at its top then, and this click used to drop\n         the old label's filing and its witness row FIRST and ask vaultFile to put them back after - so the row was gone\n         for good, the item unfiled, and the status said \"fixed\". It waits now, in words, before anything is touched.\n         (Inline, not the helper above: a law cuts this door on its own.) */\n      var _bhFix = (typeof window._vaultBasisHeld === 'function') ? window._vaultBasisHeld() : null;\n      if (false){ status('⚠ the socket fix waits - ' + _bhFix"},
    {"why": "REG-2415 - a mule is deleted while the vault it stands on is held",
     "file": "bible.html", "matches": 1,
     "find": "    if (_heldDel){ try { status('⚠ ' + m.name + ' was not deleted - ' + _heldDel); } catch (eS) {} return; }\n",
     "replace": ""},
    {"why": "REG-2415 - the witness store is not asked as the module loads, so nothing names or holds it until a door reads it",
     "file": "bible.html", "matches": 1,
     "find": "  try { _provAll(); } catch (eP0) {}\n",
     "replace": ""},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
