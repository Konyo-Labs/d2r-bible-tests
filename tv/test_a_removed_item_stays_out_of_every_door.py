# -*- coding: utf-8 -*-
"""#154 (REG-2845, REG-2846) - AN ITEM HE REMOVED, OR WIPED, STAYS OUT: one removal rule at every door that owns a name.

His words, 2026-10-28 19:25: "i have to wipe the items and then do them one by one ... but wont these keep coming back?"
Measured on the whole page in node:
  * after his X: an OLD read through tvVaultRegister owned the item again. So did the console's sweep ledger, whose
    witness carries no time. _removedAfter guarded only the read route and the folder scan;
  * after Wipe items: no removal was recorded at all, so every read (old, newer, the sweep) owned it again.

Now:
  * window._ownedAdd (the one door every add passes) and the register (before its two-session hold) ask ONE rule,
    window._vaultRemovedHold. The filing door asks it as well;
  * a read older than his removal stays out, and so does a read whose time cannot be told (UNKNOWN is never newer);
  * a NEWER dated read comes back, by design, and his own hand always does;
  * Wipe items notes every name it took out as removed at the wipe's time (REG-2846). The toolbar's Undo loads the
    snapshot taken before the wipe, so it puts the items back and the record as it was.

Each case below is a fresh page in node, driven on its real doors: tvVaultRegister, vaultAccumApply (the sweep ledger),
_ownedAdd as the photo intake calls it, and vaultHandAdd. The wipe is driven through its own scope and the note the door
writes. The door's wiring is pinned by its source. RED_PROOF below.
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

BIBLE = os.path.join(HERE, "..", "bible.html")
PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*'); localStorage.setItem('d2r_vaultAutoIntake', 'on');\n")

TMPL = r"""
(function(){
var W = window, N = 'Harlequin Crest (Shako)', OLD = Date.parse('2026-10-20T08:00:00.000Z');
function own(){ return owned.has(N); }
function reg(ms, a, b){ var at = ms == null ? undefined : new Date(ms).toISOString(), cell = { x: 3, y: 2, container: 'stash' };
  return W.tvVaultRegister('Harlequin Crest', { by: 'tv-register', lane: 'stash', loc: 'stash', scene: 'stash', holder: 'MULE1', at: at, cell: cell,
    sessions: [{ session: a, frame: a + '_f', lane: 'stash', conf: 0.9, cell: cell, holder: 'MULE1', at: at },
               { session: b, frame: b + '_f', lane: 'stash', conf: 0.9, cell: cell, holder: 'MULE1', at: at }] }); }
function sweep(a, b){ return W.vaultAccumApply({ items: [{ name: 'Harlequin Crest', kind: 'item', lane: 'stash', scene: 'stash', conf: 0.9,
  witnesses: [{ session: a, frame: a + '_f', lane: 'stash', conf: 0.9 }, { session: b, frame: b + '_f', lane: 'stash', conf: 0.9 }] }] }); }
var r0 = reg(OLD - 3600e3, 'a1', 'a2'); H.flush(60, 3);
OUT.before = own();
var undo = (typeof W._vaultProfileBuild === 'function') ? W._vaultProfileBuild() : null;   /* the snapshot the toolbar Undo takes */
var GONE = '%(gone)s';
if (GONE === 'card') W.vaultRemove([N], { lane: 'card-click', why: 'his X on the card' });
else {
  var names = []; owned.forEach(function(n){ names.push(n); });
  var S = W._VAULT_RESET_SCOPE; S.doors.vaultWipeItems.forEach(function(p){ var c = S.clears[p]; if (!c.later) c.clear(); });
  OUT.noted = W._vaultWipeRemovalNote(names, Date.now());   /* exactly what the door writes after its reset */
}
H.flush(60, 3);
var NOW = Date.now();
OUT.after = own();
var HOW = '%(how)s', r = null;
if (HOW === 'old') r = reg(OLD, 'o1', 'o2');
else if (HOW === 'oldOne'){ var c1 = { x: 3, y: 2, container: 'stash' }; r = W.tvVaultRegister('Harlequin Crest', { by: 'tv-register', lane: 'stash', loc: 'stash', scene: 'stash',
  holder: 'MULE1', at: new Date(OLD).toISOString(), cell: c1, sessions: [{ session: 'q1', frame: 'q1_f', lane: 'stash', conf: 0.9, cell: c1, holder: 'MULE1' }] }); }
else if (HOW === 'undatedSweep') r = sweep('w1', 'w2');
else if (HOW === 'oldSweep') r = sweep('s_' + OLD + '_1', 's_' + (OLD + 1) + '_2');
else if (HOW === 'intakeOld') r = W._ownedAdd(N, { source: 'intake-read', by: 'the photo intake', ts: new Date(OLD).toISOString() });
else if (HOW === 'new') r = reg(NOW + 3600e3, 'n1', 'n2');
else if (HOW === 'newSweep') r = sweep('s_' + (NOW + 3600e3) + '_1', 's_' + (NOW + 3600e3 + 1) + '_2');
else if (HOW === 'hand') r = W.vaultHandAdd(N, new Date().toISOString(), {});
else if (HOW === 'undo'){
  var P = W._vaultProfileParse(undo);
  Object.keys((P && P.stores) || {}).forEach(function(k){ var v = P.stores[k]; if (v === null) W.LSR.removeItem(k); else W.LSR.setItem(k, v); });
  try { owned.clear(); JSON.parse(W.LSR.getItem('d2r_owned') || '[]').forEach(function(n){ owned.add(n); }); } catch (e) {}
  r = reg(OLD, 'u1', 'u2');   /* an old read of an item he has again is only a re-read */
}
H.flush(60, 3);
var rmAt = null; try { rmAt = JSON.parse(W.LSR.getItem('d2r_vaultRemovedAt') || '{}'); } catch (e) { rmAt = 'UNREADABLE'; }
var sighted = null; try { sighted = Object.keys(JSON.parse(W.LSR.getItem('d2r_vaultSighted') || '{}')); } catch (e) { sighted = 'UNREADABLE'; }
OUT.result = { how: HOW, owned: own(), ok: r ? (r.ok === undefined ? null : !!r.ok) : null, sighted: sighted, refused: r && (r.refused || null), why: r && (r.why || (r.held && r.held.why) || null),
               held: !!(r && r.held), removedKeys: rmAt && typeof rmAt === 'object' ? Object.keys(rmAt) : rmAt };
OUT.errors = H.errors.slice(0, 5);
})();
"""

OUT_HOWS = ("old", "oldOne", "undatedSweep", "oldSweep", "intakeOld")
BACK_HOWS = ("new", "newSweep", "hand")


def _run(gone, how):
    return VPN.run(TMPL % {"gone": gone, "how": how}, prelude=PRELUDE, timeout=300)


class ARemovedItemStaysOutOfEveryDoor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = {}
        for gone in ("card", "wipe"):
            for how in OUT_HOWS + BACK_HOWS:
                cls.o[(gone, how)] = _run(gone, how)
        cls.o[("wipe", "undo")] = _run("wipe", "undo")
        with open(BIBLE, encoding="utf-8") as f:
            cls.src = f.read()

    def test_the_pages_booted_and_the_item_was_his_then_gone(self):
        for k, o in self.o.items():
            self.assertEqual(o["__boot"]["errors"], [], (k, o["__boot"]))
            self.assertEqual(o["errors"], [], k)
            self.assertEqual((o["before"], o["after"]), (True, False), "PREMISE %r: it was not owned, then gone: %r" % (k, o))

    def test_an_old_or_undated_read_stays_out_after_his_x(self):
        for how in OUT_HOWS:
            r = self.o[("card", how)]["result"]
            self.assertFalse(r["owned"], "after his X, %s brought it back: %r" % (how, r))

    def test_an_old_or_undated_read_stays_out_after_a_wipe(self):
        for how in OUT_HOWS:
            r = self.o[("wipe", how)]["result"]
            self.assertFalse(r["owned"], "after Wipe items, %s brought it back: %r" % (how, r))

    def test_the_register_refuses_before_it_holds_or_files(self):
        for gone in ("card", "wipe"):
            for how in ("old", "oldOne"):
                r = self.o[(gone, how)]["result"]
                self.assertEqual((r["ok"], r["refused"]), (False, "removed"), "%s/%s: the register answered as if it took the read: %r" % (gone, how, r))
                self.assertEqual(r["sighted"], [], "%s/%s: a read his removal outranks was held for a second session: %r" % (gone, how, r))
                self.assertIn("is OLDER", r["why"] or "", r)

    def test_the_refusal_says_why(self):
        u = self.o[("wipe", "intakeOld")]["result"]
        self.assertTrue(u["held"], u)

    def test_a_newer_dated_read_and_his_hand_bring_it_back(self):
        for gone in ("card", "wipe"):
            for how in BACK_HOWS:
                r = self.o[(gone, how)]["result"]
                self.assertTrue(r["owned"], "after %s, a %s read did not bring it back: %r" % (gone, how, r))

    def test_a_wipe_notes_each_name_it_took_out(self):
        w = self.o[("wipe", "old")]
        self.assertGreaterEqual((w.get("noted") or {}).get("noted", 0), 1, w.get("noted"))
        self.assertIn("harlequin crest", [k.lower() for k in w["result"]["removedKeys"]], w["result"])

    def test_undo_after_a_wipe_puts_the_items_and_the_record_back(self):
        r = self.o[("wipe", "undo")]["result"]
        self.assertTrue(r["owned"], "the Undo after a wipe left the item out: %r" % r)
        self.assertEqual(r["removedKeys"], [], "the Undo kept the wipe's removal record: %r" % r)

    def test_the_wipe_door_notes_what_it_took_out(self):
        code = "\n".join(l.split("//")[0] for l in re.sub(r"/\*.{0,4000}?\*/", "", self.src, flags=re.S).split("\n"))
        door = code[code.index("  window.vaultWipeItems = async function(){"):]
        door = door[:door.index("\n  };\n")]
        cap = "try { owned.forEach(function(n){ _wiped.push(n); });"
        run = "var R = await _vaultResetRun('vaultWipeItems');"
        note = "try { R.removalNoted = window._vaultWipeRemovalNote(_wiped, Date.now()); }"
        self.assertEqual((door.count(cap), door.count(run), door.count(note)), (1, 1, 1), "the wipe door's removal note is not wired")
        self.assertLess(door.index(cap), door.index(run))
        self.assertLess(door.index(run), door.index(note))


RED_PROOF = [
    {"why": "REG-2845 - the register owns a name his removal outranks again (and _ownedAdd lets it)",
     "file": "bible.html",
     "find": "    var r = window._removedAfter(name, ts);\n    if (!r) return null;\n",
     "replace": "    var r = null;\n    if (!r) return null;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2845 - a read with no time outvotes his removal",
     "file": "bible.html",
     "find": "    if (r.unknown && ts == null){\n",
     "replace": "    if (r.unknown && ts == null) return null;\n    if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2845 - the owned door never asks the removal rule",
     "file": "bible.html",
     "find": "    if (!had && typeof window._vaultRemovedHold === 'function'){\n",
     "replace": "    if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2845 - the register never asks the removal rule",
     "file": "bible.html",
     "find": "      if (!owned.has(name) && typeof window._vaultRemovedHold === 'function'){\n",
     "replace": "      if (false){\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2845 - a reel id does not date its read, so an old dated sweep read is UNKNOWN (and the newer one never comes back)",
     "file": "bible.html",
     "find": "    if (ts == null){ var sm = /^s_(\\d{13})_/.exec(String(rec.sessionId || '').split('#')[0]); if (sm) ts = +sm[1]; }   /* a reel id dates its read */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2846 - a wipe notes nothing removed",
     "file": "bible.html",
     "find": "    return window._vaultRemovalNote({ ts: ts || Date.now(), names: gone, lane: 'wipe', why: 'Wipe items' });\n",
     "replace": "    return { noted: 0 };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2846 - the wipe door never writes the note",
     "file": "bible.html",
     "find": "    try { R.removalNoted = window._vaultWipeRemovalNote(_wiped, Date.now()); } catch (eWr) { R.removalNoted = { noted: 0, why: String(eWr && eWr.message || eWr) }; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
