# -*- coding: utf-8 -*-
"""REG-3041 (#163, GrokBot on Dean's shadow 2026-10-29) - A SAVED FILING THE BOARD DOES NOT DRAW IS ASKED ABOUT, NEVER DROPPED.

Dean's saved records (d2r_vaultRecords) filed 5 items and his vault drew 1. Measured in node on those shapes (never his data):
the records are the vault's source only with a current migrate stamp and no dirty marker (v3766); otherwise the vault follows
the live model, which holds only what d2r_owned and d2r_muleAssign hold. Whether the other 4 were removed or lost is not
something the stores can settle, so his 2026-10-29 rule applies - when it cannot conclude, it asks: the Vault lists every
filing the saved records hold that the live model does not draw, says why it is not drawn, and offers "file it again" (his hand,
on the mule the current rule gives it, his old target named beside it) and "forget it" (asked first, undone on this page).
v3766's source rule is unchanged, nothing runs on its own, and a shadow is read only.

Driven on the whole page in node (vault_page_node), Dean's shapes on a fixture board. RED_PROOF below.
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

DEC, BUL, RHY, ENI, ALMA = "Aldur's Deception", "Bul-Kathos' Sacred Charge", "Aldur's Rhythm", "Enigma", "Alma Negra"


def _rec(n, mule):
    return {"recId": n + "#0", "name": n, "copyIx": 0, "kind": "filed", "mule": mule, "source": "manual"}


RECORDS = {"v": 1, "ts": 1761700000000, "seq": 3, "carUnknown": False, "dockUnknown": False,
           "records": [_rec(DEC, "sets-rest"), _rec(BUL, "sets-major"), _rec(RHY, "magic-rare"), _rec(ENI, "magic-rare"),
                       _rec(ALMA, "uni-armor")]}


def _prelude(extra):
    st = {"d2r_ownerClaim": "*", "d2r_ledgerName": "Fixture-Ledger", "d2r_owned": json.dumps([ALMA]),
          "d2r_muleAssign": json.dumps({ALMA: "uni-armor"}), "d2r_vaultRecords": json.dumps(RECORDS)}
    st.update(extra)
    return "".join("localStorage.setItem(%s, %s);" % (json.dumps(k), json.dumps(v)) for k, v in st.items())


STAMP = {"d2r_vaultRecordsMigrate": json.dumps({"ver": 1, "at": 1})}
WORLDS = {"nostamp": _prelude({}), "stamp": _prelude(STAMP), "dirty": _prelude(dict(STAMP, d2r_vaultRecordsDirty="1"))}

BODY = r"""
(function(){
var names = { dec: %(dec)s, bul: %(bul)s, rhy: %(rhy)s, eni: %(eni)s };
function A(){ return JSON.parse(LSR.getItem('d2r_muleAssign') || '{}'); }
function saved(){ var r = JSON.parse(LSR.getItem('d2r_vaultRecords') || 'null'); return r ? r.records.concat(r.savedNotDrawn || []).map(function(x){ return x.name; }).sort() : null; }
H.flush(600000, 8);
OUT.ownedBoot = Array.from(owned).sort(); OUT.assignBoot = A(); OUT.savedBoot = saved();
OUT.src = _vaultRecordsSource().records.map(function(x){ return x.name; }).sort();
OUT.live = _vaultRecords().records.map(function(x){ return x.name; }).sort();
OUT.list = window._vaultSavedNotDrawn();
OUT.paint = (function(){ var L = window._vaultSavedLeftPaint(); var el = document.getElementById('vault-saved-left'); return { hidden: el.hidden, html: el.innerHTML }; })();
if (%(act)s) {
  window._tvdShadow = { owner: 'Dean' };
  OUT.shFile = window._vaultSavedFileAgain(names.rhy); OUT.shForget = window._vaultSavedForget(names.eni);
  window._vaultSavedLeftPaint(); OUT.shHtml = document.getElementById('vault-saved-left').innerHTML;
  window._tvdShadow = null;
  OUT.file = window._vaultSavedFileAgain(names.rhy);
  OUT.rhyOwned = owned.has(names.rhy); OUT.rhyAssign = A()[names.rhy] || null;
  OUT.rhyProv = (JSON.parse(LSR.getItem('d2r_vaultProv') || '{}')[names.rhy] || {}).source || null;
  OUT.listAfterFile = window._vaultSavedNotDrawn().rows.map(function(r){ return r.name; }).sort();
  OUT.forget = window._vaultSavedForget(names.eni); OUT.savedAfterForget = saved();
  window._vaultSavedLeftPaint(); OUT.undoHtml = document.getElementById('vault-saved-left').innerHTML;
  OUT.unforget = window._vaultSavedUnforget(); OUT.savedAfterUndo = saved();
  OUT.listAfter = window._vaultSavedNotDrawn().rows.map(function(r){ return r.name; }).sort();
}
})();
"""

_RUNS = {}


def page(world):
    if world not in _RUNS:
        body = BODY % {"dec": json.dumps(DEC), "bul": json.dumps(BUL), "rhy": json.dumps(RHY), "eni": json.dumps(ENI),
                       "act": "true" if world == "nostamp" else "false"}
        _RUNS[world] = VPN.run(body, prelude=WORLDS[world], timeout=300)
    return _RUNS[world]


def rows(o):
    return dict((r["name"], r) for r in o["list"]["rows"])


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class ASavedFilingTheBoardDoesNotDrawIsAskedAbout(unittest.TestCase):

    def test_the_premise_every_world_boots(self):
        for w in WORLDS:
            self.assertEqual(page(w)["__boot"]["errors"], [], "%s: %r" % (w, page(w)["__boot"]))

    def test_v3766_is_unchanged_the_saved_records_are_the_source_only_when_stamped_and_clean(self):
        self.assertEqual(page("stamp")["src"], sorted([DEC, BUL, RHY, ENI, ALMA]))
        for w in ("nostamp", "dirty"):
            self.assertEqual(page(w)["src"], page(w)["live"], "%s: the source is not the live model" % w)
            self.assertNotIn(RHY, page(w)["src"])

    def test_nothing_is_filed_or_forgotten_on_its_own(self):
        o = page("nostamp")
        self.assertEqual(o["ownedBoot"], [ALMA]); self.assertEqual(o["assignBoot"], {ALMA: "uni-armor"})
        self.assertEqual(o["savedBoot"], sorted([DEC, BUL, RHY, ENI, ALMA]))

    def test_each_filing_the_live_model_lacks_is_listed_with_why(self):
        o = page("nostamp")
        self.assertTrue(o["list"]["ok"]); self.assertEqual(o["list"]["source"], "live")
        self.assertIn("no current stamp", o["list"]["why"])
        self.assertEqual(sorted(rows(o)), sorted([DEC, BUL, RHY, ENI]), "a saved filing is missing, or a drawn one is listed")
        self.assertIn("did not read back", page("dirty")["list"]["why"])
        self.assertEqual(page("stamp")["list"]["rows"], [], "a drawn filing was listed")
        self.assertTrue(page("stamp")["paint"]["hidden"])

    def test_the_offer_is_the_current_rules_home_with_his_old_target_beside_it(self):
        R = rows(page("nostamp"))
        self.assertEqual((R[RHY]["old"], R[RHY]["offer"]), ("magic-rare", "sets-rest"))
        self.assertEqual((R[ENI]["old"], R[ENI]["offer"]), ("magic-rare", "shared"))
        self.assertEqual((R[DEC]["old"], R[DEC]["offer"]), ("sets-rest", "sets-rest"))
        self.assertEqual((R[BUL]["old"], R[BUL]["offer"], R[BUL]["ruleName"]), ("sets-major", "sets-major", "THROW OUT"),
                         "a filing the rule would throw out lost his own target")
        h = page("nostamp")["paint"]["html"]
        self.assertIn("saved on MAGIC &amp; RARE; the rule now files it on SETS-REST", h)
        self.assertIn("file it again on SETS-REST", h)
        self.assertIn("forget it", h)

    def test_file_it_again_is_his_hand_on_the_offered_mule(self):
        o = page("nostamp")
        self.assertTrue(o["file"]["ok"], o["file"])
        self.assertEqual((o["rhyOwned"], o["rhyAssign"], o["rhyProv"]), (True, "sets-rest", "hand"))
        self.assertNotIn(RHY, o["listAfter"])

    def test_a_write_never_drops_the_other_saved_filings(self):
        self.assertEqual(page("nostamp")["listAfterFile"], sorted([DEC, BUL, ENI]),
                         "filing one saved item wiped the others from the list")

    def test_forget_leaves_the_saved_records_and_undo_puts_it_back(self):
        o = page("nostamp")
        self.assertTrue(o["forget"]["ok"], o["forget"])
        self.assertNotIn(ENI, o["savedAfterForget"] or [])
        self.assertIn("undo forgetting Enigma", o["undoHtml"])
        self.assertTrue(o["unforget"]["ok"]); self.assertIn(ENI, o["savedAfterUndo"])

    def test_a_shadow_is_read_only(self):
        o = page("nostamp")
        self.assertFalse(o["shFile"]["ok"]); self.assertIn("read only", o["shFile"]["why"])
        self.assertFalse(o["shForget"]["ok"])
        self.assertIn("Read only", o["shHtml"]); self.assertNotIn("data-saved-act", o["shHtml"])


RED_PROOF = [
    {"why": "REG-3041 - a dirty store is drawn again (v3766 broken)",
     "file": "bible.html",
     "find": "      if (typeof _vrRecDirty === 'function' && _vrRecDirty()) return { store: null, why: 'the last records write did not read back' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - a saved filing the live model lacks is not listed",
     "file": "bible.html",
     "find": "      if (!home || !_vrSavedUndrawn(String(r.name), drawn)) return;\n",
     "replace": "      if (!home || true) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - the offer keeps the old target even when the rule homes it elsewhere",
     "file": "bible.html",
     "find": "offer = (ruleM && ruleId !== home) ? ruleId : home,",
     "replace": "offer = home,",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - the offer follows the rule even to THROW OUT",
     "file": "bible.html",
     "find": "ruleM = (ruleId && ruleId !== '__throwout') ? muleById(ruleId) : null;",
     "replace": "ruleM = ruleId ? (muleById(ruleId) || { name: ruleId }) : null;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - a shadow files it again",
     "file": "bible.html",
     "find": "    if (window._tvdShadow) return { ok: false, why: \"this is another PC's console, read only - it is filed on that PC\" };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - file it again only owns it and never files it",
     "file": "bible.html",
     "find": "    var fl = window.vaultFile(name, { by: 'hand', at: at, where: where }, { mule: to, move: assign[name] != null });\n",
     "replace": "    var fl = { ok: true };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - a write drops the saved filings nobody can explain",
     "file": "bible.html",
     "find": "    if (_carry.length) store.savedNotDrawn = _carry;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - a set piece saved under its bare name is asked about after it is drawn under its slot name",
     "file": "bible.html",
     "find": "    return !twins.some(function(t){ return drawn[t]; }) && !drawn[name];\n",
     "replace": "    return !drawn[name];\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3041 - forget leaves no undo",
     "file": "bible.html",
     "find": "    _vaultSavedForgot.push({ name: name, rows: inRec, side: inSide });\n    return { ok: true, forgot: name, rows: gone.length };\n",
     "replace": "    return { ok: true, forgot: name, rows: gone.length };\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
