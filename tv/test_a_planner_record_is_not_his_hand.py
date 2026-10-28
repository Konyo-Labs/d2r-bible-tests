# -*- coding: utf-8 -*-
"""#111 (REG-2785) - A PLANNER RECORD IS NOT HIS HAND. Auto-Sort skipped the picture check for any dock name with one.

_plannerHandRow answers "his hand put this here" for his Auto-Sort click, which then files the dock name to its mule (and
past the REG-2223 chronicle gate in the shared-stash arm) without the stash picture every other dock name needs. It read the
ROW's words (the Vault planner, + Add an item) and also answered true for any name with a d2r_plannerMade record. That
record is kept per NAME for the base he built (the cell's picture, footprint and hover read it) and nothing takes it out when
the item leaves: vaultRemove drops the witness row and keeps the record.

Measured on the whole page in node (tv/vault_page_node.py, a fresh store): Obedience picked in the planner (filed to
RUNEWORDS), removed, then read off a Chronicle page in two sessions - a found-ever tick with no stash picture, which the dock
holds as loose. His Auto-Sort click filed it to RUNEWORDS as his hand. Grief, the same road, went to the shared stash past
REG-2223's gate. Now both stay in "no picture yet", and a row that carries his hand (the planner's words, + Add an item, the
planner receipt a cell X demotes a filing back to) still files without a picture.
RED_PROOF below.
"""
import io
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass
import vault_page_node as VPN  # noqa: E402

PRELUDE = "localStorage.setItem('d2r_ownerClaim', '*'); localStorage.setItem('d2r_vaultAutoIntake', 'on');\n"

# Obedience (r92) routes to the RUNEWORDS mule, Grief (r47) is war gear routed to the shared stash: one name per Auto-Sort arm.
BODY = r"""
(function(){
var W = window;
try { W.renderVault(); } catch (e) { OUT.renderErr = String(e && e.message || e); }
H.flush(60, 3);
function assignOf(n){ var a = {}; try { a = JSON.parse(W.LSR.getItem('d2r_muleAssign') || '{}'); } catch (e) {} return a[n] == null ? null : a[n]; }
function row(n){ var p = {}; try { p = JSON.parse(W.LSR.getItem('d2r_vaultProv') || '{}'); } catch (e) {} return p[n] || null; }
function homes(n){ return (W._vaultRecords().records || []).filter(function(x){ return x.name === n; }).map(function(x){ return x.kind; }); }
[['Obedience', 'r92'], ['Grief', 'r47']].forEach(function(p){
  var n = p[0], o = {};
  var it = W._cbItem(p[1]), bases = W._cbBasesOf(it) || [];
  var pk = W.vaultPlannerFile({ id: p[1], base: bases[0], affixes: [], sockets: 0 }, 'law-' + n);
  o.pick = { ok: !!(pk && pk.ok), filed: !!(pk && pk.filed), mule: (pk && pk.mule) || null };
  var rm = W.vaultRemove([n], { lane: 'law', quiet: true, exact: true, why: 'he took it out' });
  o.removed = !!(rm && rm.removed && rm.removed.indexOf(n) >= 0);
  o.recordKept = !!W._vpMadeOf(n);
  /* REG-2845 - the read comes AFTER his removal (an older one never brings a removed item back) */
  var rg = W.tvVaultRegister(n, { by: 'tv-register', loc: 'chronicle', scene: 'chronicle', at: new Date(Date.now() + 60000).toISOString(),
                                  sessions: [{ session: 'c1_' + n, frame: 'f1_' + n }, { session: 'c2_' + n, frame: 'f2_' + n }] });
  o.registered = !!(rg && rg.ok);
  o.looks = ((row(n) || {}).looks || []).map(function(l){ return l.loc; });
  o.inDock = (W._vaultDockNames() || []).indexOf(n) >= 0;
  OUT[n] = o;
});
var r = W.vaultAutoSortByHand(); H.flush(60, 3);
OUT.sort = { filed: r.filed, noPicture: r.noPicture.slice().sort(), rows: r.rows };
['Obedience', 'Grief'].forEach(function(n){
  OUT[n].assign = assignOf(n); OUT[n].kinds = homes(n); OUT[n].stillInDock = (W._vaultDockNames() || []).indexOf(n) >= 0;
  OUT[n].rowWhere = (row(n) || {}).where || null;
});
OUT.errors = H.errors.slice();
})();
"""


def _src():
    return io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()


def _cut(s, a, b):
    i = s.find(a)
    j = s.find(b, i + 1)
    if i < 0 or j < 0:
        raise AssertionError("anchor not found: %r / %r" % (a[:60], b[:60]))
    return s[i:j]


class APlannerRecordIsNotHisHand(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted_and_the_road_was_walked(self):
        o = self.o
        self.assertEqual(o["__boot"]["errors"], [], o["__boot"])
        self.assertNotIn("renderErr", o, o.get("renderErr"))
        self.assertEqual(o["errors"], [])
        for n, mule in (("Obedience", "runewords"), ("Grief", "shared")):
            p = o[n]
            self.assertEqual(p["pick"], {"ok": True, "filed": True, "mule": mule}, "PREMISE: the planner pick of %s: %r" % (n, p))
            self.assertTrue(p["removed"], "PREMISE: %s was not removed: %r" % (n, p))
            self.assertTrue(p["recordKept"], "PREMISE: the removal took the planner record too, so nothing here is stale: %r" % p)
            self.assertTrue(p["registered"], "PREMISE: the Chronicle read did not register %s: %r" % (n, p))
            self.assertEqual(p["looks"], ["chronicle"], "PREMISE: the row is not a chronicle-only found-ever tick: %r" % p)
            self.assertTrue(p["inDock"], "PREMISE: %s is not loose in the dock before the click: %r" % (n, p))

    def test_a_found_ever_tick_with_a_stale_record_waits_for_a_picture(self):
        o = self.o
        self.assertEqual(o["sort"]["noPicture"], ["Grief", "Obedience"],
                         "a dock name with only a planner record skipped the picture check: %r" % o["sort"])
        self.assertEqual(o["sort"]["rows"], [], o["sort"])
        for n in ("Obedience", "Grief"):
            p = o[n]
            self.assertIsNone(p["assign"], "%s was filed by his click on a record, not his hand: %r" % (n, p))
            self.assertEqual(p["kinds"], ["loose"], "%s left the dock: %r" % (n, p))
            self.assertTrue(p["stillInDock"], p)
            self.assertIsNone(p["rowWhere"], "the found-ever row was rewritten as an Auto-Sort hand filing: %r" % p)

    def test_a_row_that_carries_his_hand_still_skips_the_picture(self):
        """The shipped _plannerHandRow, cut from the page, with the planner store answering a record for every name."""
        hand_fn = _cut(_src(), "  function _plannerHandRow(name, row){\n", "  function _plannerPropose(name){\n")
        self.assertNotIn("_vpMadeOf", hand_fn, "the hand gate reads the planner store again")
        prog = (
            "var window = globalThis;\n"
            "window._vpMadeOf = function(n){ return { id: 'r92', base: 'brn', baseName: 'Brandistock', q: 'r' }; };\n"
            + hand_fn
            + "process.stdout.write(JSON.stringify({\n"
            "  planner: _plannerHandRow('Insight', { kind: 'owned', source: 'hand', by: 'the Vault planner', where: 'the Vault planner', looks: [] }),\n"
            "  filing: _plannerHandRow('Insight', { mule: 'runewords', by: 'hand', where: 'the Vault planner — your search filed it where a reel of it would go' }),\n"
            "  ownedBy: _plannerHandRow('Insight', { mule: 'runewords', by: 'hand', where: 'x', ownedBy: { by: 'the Vault planner', where: 'the Vault planner' } }),\n"
            "  add: _plannerHandRow('Titan', { source: 'hand', by: '+ Add an item', where: 'the Vault (+ Add an item)', looks: [] }),\n"
            "  chronicle: _plannerHandRow('Obedience', { kind: 'owned', source: 'tv-register', by: 'tvVaultRegister', where: null, looks: [{ loc: 'chronicle', scene: 'chronicle' }] }),\n"
            "  none: _plannerHandRow('Obedience', null)\n"
            "}));\n"
        )
        p = subprocess.run([VPN.NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, (p.stderr or p.stdout)[-1500:])
        r = json.loads(p.stdout)
        self.assertTrue(r["planner"] and r["filing"] and r["ownedBy"] and r["add"], "a row that carries his hand lost it: %r" % r)
        self.assertFalse(r["chronicle"], "a Chronicle receipt passed as his hand because the name has a planner record")
        self.assertFalse(r["none"], "a name with no row passed as his hand because it has a planner record")


RED_PROOF = [
    {"why": "REG-2785 - the hand gate counts any planner record as his hand again",
     "file": "bible.html",
     "find": "    if (blob.indexOf('+ Add an item') >= 0) return true;\n    /* REG-2785 (#111)",
     "replace": "    if (blob.indexOf('+ Add an item') >= 0) return true;\n"
                "    try { if (typeof window._vpMadeOf === 'function' && window._vpMadeOf(name)) return true; } catch (e2) {}\n"
                "    /* REG-2785 (#111)",
     "matches": 1, "needs": "node"},
    {"why": "REG-2785 - the shared-stash arm files a chronicle-only tick past the REG-2223 gate",
     "file": "bible.html",
     "find": "        if (!_plannerHandRow(name, row) && _isChronicleOnlyRow(row)){ out.noPicture.push(name); return; }\n",
     "replace": "        if (false && _isChronicleOnlyRow(row)){ out.noPicture.push(name); return; }\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
