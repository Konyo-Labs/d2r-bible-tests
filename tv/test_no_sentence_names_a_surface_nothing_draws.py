# -*- coding: utf-8 -*-
"""#154 (REG-2834) - NO SENTENCE NAMES A SURFACE NOTHING DRAWS. The same class as REG-2831's missing undo.

Two sentences told him where to undo, and neither place exists:
  * the planner's take-back: "<name> is taken back (undo it from Recently removed)" - no surface draws a Recently removed
    list on the board or the console; the removal journal is read by vaultRestoreLast(), a console call;
  * the un-tick redo's bar: "Put it back from the vault removal list" - no such list either, and vaultRestoreLast() puts
    back the NEWEST batch, which here is the other removal. Measured on the whole page in node: after an un-tick, another
    removal and the re-tick, the item is neither owned nor filed.
Swept: bible.html and tv/control_ui.html, every "recently removed" and "removal list" outside a comment - these two were
all. Now the take-back arms the toolbar's Undo (the board's undo surface, #145) and its sentence names that chip only when
it holds this take-back; the redo's bar says to add it again from the Vault's own add card (✚ Add an item), which owns it
by his hand and lets the router file it. Driven on the whole page in node, and the two surfaces checked to be drawn.
RED_PROOF below.
"""
import io
import json
import os
import re
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

FILES = ("bible.html", os.path.join("tv", "control_ui.html"))
#: names of undo surfaces that no element draws - a sentence may not send him to one
PHANTOMS = re.compile(r"recently removed|removal list|removed list", re.I)


def _code_only(text):
    """the file with its comments taken out: /* */ blocks, <!-- --> blocks, and // comments that follow code or open a line"""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return re.sub(r"(^|[;{}),])[ \t]*//[^\n]*", r"\1", text, flags=re.M)


PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n"
           "localStorage.setItem('d2r_owned', JSON.stringify([\"Nightwing's Veil\", 'Lightsabre']));\n"
           "localStorage.setItem('d2r_muleAssign', JSON.stringify({\"Nightwing's Veil\": 'uni-armor', 'Lightsabre': 'uni-weap'}));\n")

BODY = r"""
(function(){
var W = window;
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
/* 1 - the planner's take-back: a 4os Monarch picked (it files), then the same pick re-rolled to 3 sockets */
var db = W._cbDb(), code = Object.keys(db.b).find(function(c){ return db.b[c][0] === 'Monarch'; });
function ent(n){ var e = W._cbEntryFor(W._cbItem('b:' + code)); e.sockets = n; return e; }
var a = W.vaultPlannerFile(ent(4), 'law-tb');
var b = W.vaultPlannerFile(ent(3), 'law-tb');
var u = W._vaultUndo, P = u ? W._vaultProfileParse(u.text) : null, has = false;
try { has = JSON.parse(P.stores['d2r_owned']).indexOf('Monarch (4os)') >= 0; } catch (e) {}
var d = (P && P.ok) ? ((W._vaultProfileDiff(P.stores) || []).filter(function(r){ return r.store === 'd2r_owned'; })[0] || null) : null;
OUT.takeBack = { first: a && a.filed, why: b && b.why, ownedNow: owned.has('Monarch (4os)'), undo: u && u.what, has: has, changed: !!(d && d.changed) };
/* 2 - the un-tick redo: un-tick, another removal, the re-tick */
var N = "Nightwing's Veil";
W.toggleOwned(N); H.flush(60, 3);
W.vaultUnown('Lightsabre'); H.flush(60, 3);
W.toggleOwned(N); H.flush(60, 3);
var lt = null; try { lt = JSON.parse(W.LSR.getItem('d2r_lastTick') || 'null'); } catch (e) {}
OUT.redo = { owned: owned.has(N), say: lt && lt.redo };
OUT.errors = H.errors.slice();
})();
"""


class NoSentenceNamesASurfaceNothingDraws(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_no_sentence_sends_him_to_a_list_nothing_draws(self):
        hits = []
        for f in FILES:
            code = _code_only(io.open(os.path.join(ROOT, f), encoding="utf-8").read())
            for m in PHANTOMS.finditer(code):
                hits.append("%s: ...%s..." % (f, code[max(0, m.start() - 60):m.end() + 30].replace("\n", " ")))
        self.assertEqual(hits, [], "a sentence names an undo surface no element draws: %r" % hits)

    def test_the_surfaces_the_sentences_name_are_drawn(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])
        page = io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
        self.assertEqual(page.count('<h3 class="vault-tool-h" id="vault-tool-add-h">✚ Add an item</h3>'), 1,
                         "the Vault's add card (the redo's bar sends him there) is not in the page's markup")
        self.assertRegex(page, r'id="vault-chip-undo"[^>]*>↶ Undo <span id="vault-chip-undo-what">',
                         "the toolbar's Undo chip (the take-back's sentence names it) is not in the page's markup")

    def test_the_take_back_names_an_undo_that_holds_it(self):
        t = self.o["takeBack"]
        self.assertTrue(t["first"], "PREMISE: the 4os Monarch was not filed: %r" % t)
        self.assertFalse(t["ownedNow"], "PREMISE: the re-roll did not take the 4os copy back: %r" % t)
        self.assertIn("Monarch (4os) is taken back (↶ Undo in the toolbar puts it back)", t["why"] or "", t)
        self.assertEqual(t["undo"], "the take-back of Monarch (4os)", "the toolbar's Undo does not hold the take-back: %r" % t)
        self.assertTrue(t["has"] and t["changed"], "the toolbar's Undo would not put the copy back: %r" % t)

    def test_the_redo_bar_sends_him_to_the_add_card(self):
        r = self.o["redo"]
        self.assertFalse(r["owned"], "PREMISE: the vault part came back, so there is nothing to say: %r" % r)
        self.assertIn("✚ Add an item in the Vault", r["say"] or "", "the redo's bar names no real surface: %r" % r)


RED_PROOF = [
    {"why": "REG-2834 - the planner's take-back sends him to 'Recently removed' again",
     "file": "bible.html",
     "find": "(_undoVpOk ? ' (↶ Undo in the toolbar puts it back)' :",
     "replace": "(_undoVpOk ? ' (undo it from Recently removed)' :",
     "matches": 1, "needs": "node"},
    {"why": "REG-2834 - the redo's bar sends him to 'the vault removal list' again",
     "file": "bible.html",
     "find": "todo: 'add it again from ✚ Add an item in the Vault' };",
     "replace": "todo: 'put it back from the vault removal list' };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2834 - the take-back arms no undo, so the toolbar's chip would undo some older change",
     "file": "bible.html",
     "find": "      var _undoVpOk = !!(_undoVp && typeof window._vaultUndoTake === 'function' && window._vaultUndoTake('the take-back of ' + nm, '', _undoVp));\n",
     "replace": "      var _undoVpOk = true;\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
