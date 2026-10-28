# -*- coding: utf-8 -*-
"""REG-2923 (#252) - THE UPLOAD LOGGER, THE WISHLIST TITLE AND THE LOOT FILTER'S NAME ARE HIS ONLY ON HIS LEDGER.

His rule (2026-09-27): every personal surface is per-PC. Three defaults named him on every PC:
  * the photo-upload logger defaulted to 'Konyo', so another PC's journal recorded its uploads as his and the tally
    counted every untagged session as his;
  * the wishlist export was titled "# Konyo Wishlist";
  * the endgame loot filter was named 'KonyoEndgame<N>' (his ledger's own name) on any claimed board, in the export and on
    the card's two labels.
On his ledger (the v2692 gate, `_seedsBelongHere`) nothing changes. Anywhere else the logger is unset until someone says
who (the chip says so, the journal stores no name), the export is "# Wishlist", and the filter is named after the board's
own ledger - 'Cousin' on a guest, as before.

Driven on the whole page in node (vault_page_node), three fixture worlds: HIS (claimed, ledger KonyoEndgame), OTHER
(claimed, ledger Deans-Own-Ledger) and GUEST (unclaimed). The journal starts with one untagged session and one of Dean's.
The card's labels after the filter engine's own repaint (refreshLootFilterCount) need a real DOM: the Chrome spec
tests/v252_his_names_stay_on_his_ledger.spec.ts holds that half. RED_PROOF below.
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');"
JOURNAL = json.dumps(json.dumps([
    {"ts": 1761600000000, "items": ["Shako"], "pf": []},
    {"ts": 1761500000000, "u": "Dean", "items": ["Arachnid Mesh"], "pf": []},
]))
LABELS = ("(function(){ var a = document.getElementById('lf-endgame-brand'); a.textContent = 'KonyoEndgame';"
          " var b = document.getElementById('lf-endgame-brand-btn'); b.textContent = 'KonyoEndgame'; })();")
WORLDS = {
    "his": CLAIM + "localStorage.setItem('d2r_ledgerName', 'KonyoEndgame');",
    "other": CLAIM + "localStorage.setItem('d2r_ledgerName', 'Deans-Own-Ledger');",
    "guest": "",
}
# the journal's writer lives inside the intake scope; the law reaches it beside the page's own export of renderJournal
PATCHES = [("  try { window.renderJournal = renderJournal; } catch(e){}",
            "  try { window.renderJournal = renderJournal; window.__journalAddForLaw = journalAdd; } catch(e){}", 1)]


def prelude(world):
    return WORLDS[world] + "localStorage.setItem('d2r_intakeLog', %s);" % JOURNAL + LABELS


BODY = r"""
(function(){
var ERR = [];
function tryit(k, f){ try { f(); } catch (e) { ERR.push(k + ': ' + String(e && e.message || e)); } }
function grab(id){ var e = document.getElementById(id); return e ? String(e.innerHTML || '') : ''; }
OUT.seeds = window._seedsBelongHere === true;
OUT.logger = window.getIntakeLogger();
tryit('blank', function(){ window.setIntakeLogger(''); OUT.loggerAfterBlank = window.getIntakeLogger(); });
tryit('journal', function(){ window.renderJournal(); OUT.journal = grab('vault-journal'); });
tryit('add', function(){ window.__journalAddForLaw(['Shako'], []);
  var j = JSON.parse(window.LSR.getItem('d2r_intakeLog') || '[]'); OUT.added = j.length ? (j[0].u === undefined ? '(absent)' : j[0].u) : '(none)'; });
tryit('wishlist', function(){
  navigator.clipboard.writeText = function(t){ OUT.md = String(t); return Promise.resolve(); };
  wishlist.add('Harlequin Crest'); window.exportWishlistAsMarkdown(); });
OUT.brand = window._lfBrandName();
tryit('filter', function(){ OUT.filterName = window.buildEndgameFilter().name; });
OUT.labels = [document.getElementById('lf-endgame-brand').textContent, document.getElementById('lf-endgame-brand-btn').textContent];
OUT.ERR = ERR;
})();
"""

_RUNS = {}


def page(world):
    if world not in _RUNS:
        _RUNS[world] = VPN.run(BODY, prelude=prelude(world), patches=PATCHES, timeout=600)
    return _RUNS[world]


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class HisLoggerWishlistAndFilterNamesStayHis(unittest.TestCase):

    def test_the_premise_every_world_boots_and_draws(self):
        for w in WORLDS:
            o = page(w)
            self.assertEqual(o["__boot"]["errors"], [], "%s: %r" % (w, o["__boot"]))
            self.assertEqual(o["ERR"], [], "%s: %r" % (w, o["ERR"]))
            self.assertTrue((o.get("md") or "").startswith("# "), "%s: the wishlist export wrote nothing" % w)
            self.assertTrue(o.get("filterName"), "%s: the endgame filter built no name" % w)
        for w in ("his", "other"):
            self.assertIn("vj-logger", page(w)["journal"] or "", "%s: the journal's logger chip was not drawn" % w)
        self.assertTrue(page("his")["seeds"])
        self.assertFalse(page("other")["seeds"] or page("guest")["seeds"])

    def test_his_ledger_keeps_konyo_everywhere(self):
        o = page("his")
        self.assertEqual((o["logger"], o["loggerAfterBlank"], o["added"]), ("Konyo", "Konyo", "Konyo"))
        self.assertIn("👤 Konyo ⇄", o["journal"])
        self.assertIn("👤 Konyo ·1", o["journal"], "his untagged session is no longer his in the tally")
        self.assertTrue(o["md"].startswith("# Konyo Wishlist · "), o["md"][:60])
        self.assertEqual(o["brand"], "KonyoEndgame")
        self.assertTrue(o["filterName"].startswith("KonyoEndgame"), o["filterName"])
        self.assertEqual(o["labels"], ["KonyoEndgame", "KonyoEndgame"])

    def test_another_board_logs_as_nobody_until_it_says_who(self):
        o = page("other")
        self.assertEqual((o["logger"], o["loggerAfterBlank"]), ("", ""), "another board's uploads are logged as %r" % o["logger"])
        self.assertIsNone(o["added"], "another board's journal recorded its upload as %r" % o["added"])
        self.assertIn("who? (not set)", o["journal"])
        self.assertIn("👤 not set ·1", o["journal"], "an untagged session on another board is counted as someone's")
        self.assertIn("👤 Dean ·1", o["journal"])
        self.assertNotIn("Konyo", re.sub(r"<[^>]*>", " ", o["journal"]), "another board's journal shows his name")
        self.assertEqual(page("guest")["logger"], "")

    def test_another_board_exports_its_own_wishlist_and_filter(self):
        for w, brand in (("other", "DeansOwnLedger"), ("guest", "Cousin")):
            o = page(w)
            self.assertTrue(o["md"].startswith("# Wishlist · "), "%s: %r" % (w, o["md"][:60]))
            self.assertEqual(o["brand"], brand, w)
            self.assertTrue(o["filterName"].startswith(brand), "%s: the filter is named %r" % (w, o["filterName"]))
            self.assertNotIn("Konyo", o["filterName"])
            self.assertEqual(o["labels"], [brand, brand], "%s: the card's labels still read %r" % (w, o["labels"]))


RED_PROOF = [
    {"why": "REG-2923 - every board's uploads are logged as Konyo again",
     "file": "bible.html",
     "find": "let intakeLogger = (LS.getItem('d2r_logger') || (window._seedsBelongHere === true ? 'Konyo' : ''));\n",
     "replace": "let intakeLogger = (LS.getItem('d2r_logger') || 'Konyo');\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - clearing the logger name falls back to Konyo on every board",
     "file": "bible.html",
     "find": "intakeLogger = (String(name == null ? '' : name).trim()) || (window._seedsBelongHere === true ? 'Konyo' : '');",
     "replace": "intakeLogger = (String(name == null ? '' : name).trim()) || 'Konyo';",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - the journal stores an empty logger instead of no name",
     "file": "bible.html",
     "find": "u: ((typeof intakeLogger !== 'undefined' && intakeLogger) ? intakeLogger : null)",
     "replace": "u: (typeof intakeLogger !== 'undefined' ? intakeLogger : 'Konyo')",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - the tally counts every untagged session as his",
     "file": "bible.html",
     "find": "var u=e.u||(window._seedsBelongHere===true?'Konyo':'not set');",
     "replace": "var u=e.u||'Konyo';",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - the logger chip says nothing when nobody is set",
     "file": "bible.html",
     "find": "esc((typeof intakeLogger!=='undefined' && intakeLogger) ? intakeLogger : 'who? (not set)')",
     "replace": "esc(typeof intakeLogger!=='undefined'?intakeLogger:'Konyo')",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - every board's wishlist export is his",
     "file": "bible.html",
     "find": "  let md = `# ${window._seedsBelongHere === true ? 'Konyo ' : ''}Wishlist · ${date}\\n\\n`;",
     "replace": "  let md = `# Konyo Wishlist · ${date}\\n\\n`;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - every claimed board's filter is named after his ledger",
     "file": "bible.html",
     "find": "  if (window._seedsBelongHere === true) return 'KonyoEndgame';\n  var n = String(window._D2R_LEDGER || '').replace(/[^A-Za-z0-9]/g, '');\n  return n || 'MyEndgame';\n",
     "replace": "  return 'KonyoEndgame';\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - the exported filter's name ignores the board's ledger",
     "file": "bible.html",
     "find": "tpl.name = (opts && opts.fresh) ? 'CousinFull' : (window._lfBrandName() + window._chronicleMadeCount());",
     "replace": "tpl.name = (opts && opts.fresh) ? 'CousinFull' : ((window._isCousinShell ? 'Cousin' : 'KonyoEndgame') + window._chronicleMadeCount());",
     "matches": 1, "needs": "node"},
    {"why": "REG-2923 - the card's static labels are never repainted at boot",
     "file": "bible.html",
     "find": "if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ _lfBrandPaint(); });\n",
     "replace": "if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ });\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
