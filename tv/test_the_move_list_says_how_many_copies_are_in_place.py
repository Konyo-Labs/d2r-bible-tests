# -*- coding: utf-8 -*-
"""REG-3065 (his design 2026-10-28 18:56, #202) - THE MOVE LIST SAYS HOW MANY COPIES ARE IN PLACE: "in place N of M".

His extension to the intake design: the readout shows "in place N of M". The MOVE TASKS list said only MOVE TASKS, and the
read-only readout (window._vaultCopyAudit) said nothing of it either: nothing told him how far along he is. Now, of the
copies with a move to a home (a throw-out has no home, and a row the drain closed is gone), N are in place: proven at their
target by reads from two sessions (verified, REG-2843) or ticked by his hand (moved-manual). The head of the list says it,
its title says how many of each, and the readout carries the same numbers. With no move model yet it is UNKNOWN (null),
never "0 of 0". Driven on the whole page in node. RED_PROOF below.
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
import vault_page_node as VPN  # noqa: E402

PRELUDE = ("Object.defineProperty(navigator, 'webdriver', { get: function(){ return true; }, configurable: true });\n"
           "localStorage.setItem('d2r_ownerClaim', '*');\n")
BODY = r"""
(function(){
var W = window;
OUT.unknown = W._vaultInPlace({});
function row(status, kind){ return { name: 'X', copyIx: 0, task: { status: status, kind: kind || 'move' } }; }
var model = { tasks: [row('verified'), row('moved-manual'), row('to-move'), row('moved-elsewhere'), row('to-move', 'throw'), row('closed')], groups: [], locks: [] };
OUT.model = W._vaultInPlace(model);
var html = W._vaultMoveHtml({ tasks: model.tasks, locks: [], groups: [{ label: 'MAIN', stash: 'Stash 1', rows: model.tasks.slice(0, 4) }] });
var m = /<span class="vmv-inplace" title="([^"]*)">([^<]*)<\/span>/.exec(html);
OUT.head = m ? { text: m[2], title: m[1] } : null;
OUT.emptyHead = /vmv-inplace/.test(W._vaultMoveHtml({ tasks: [], locks: [], groups: [] }));
/* the real page: three hand adds, each with its move row; his tick puts one in place */
['Nagelring', 'Manald Heal', 'The Stone of Jordan'].forEach(function(n){ W.vaultHandAdd(n, new Date().toISOString(), {}); H.flush(60, 3); });
try { W.renderVault(); } catch (e) {} H.flush(60, 3);
W._vaultMovePaint(); H.flush(60, 3);
OUT.before = W._vaultInPlace();
var first = (W._moveModel.tasks || []).filter(function(r){ return r.task && r.task.kind !== 'throw'; })[0];
OUT.ticked = first ? first.name : null;
if (first) { W._vaultTaskTick(first.name, first.copyIx || 0); H.flush(60, 3); }
W._vaultMovePaint(); H.flush(60, 3);
OUT.after = W._vaultInPlace();
var host = String((document.getElementById('vault-move-list') || {}).innerHTML || '');
OUT.painted = (/<span class="vmv-inplace"[^>]*>([^<]*)<\/span>/.exec(host) || [])[1] || null;
OUT.audit = (W._vaultCopyAudit() || {}).inPlace || null;
OUT.errors = H.errors.slice(0, 5);
})();
"""


class TheMoveListSaysHowManyCopiesAreInPlace(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not VPN.NODE:
            raise AssertionError("node is not on this machine - this law does not skip")
        cls.o = VPN.run(BODY, prelude=PRELUDE, timeout=300)

    def test_the_page_booted(self):
        self.assertEqual(self.o["__boot"]["errors"], [], self.o["__boot"])
        self.assertEqual(self.o["errors"], [])

    def test_no_model_is_unknown_never_zero(self):
        self.assertIsNone(self.o["unknown"], self.o["unknown"])
        self.assertFalse(self.o["emptyHead"], "a list with no copies says 'in place 0 of 0'")

    def test_in_place_counts_verified_and_ticked_of_the_copies_with_a_home(self):
        m = self.o["model"]
        self.assertEqual((m["n"], m["m"], m["verified"], m["ticked"]), (2, 4, 1, 1), m)

    def test_the_head_says_it_and_its_title_says_how(self):
        h = self.o["head"]
        self.assertEqual((h or {}).get("text"), "in place 2 of 4", h)
        self.assertIn("1 seen there by two sessions, 1 ticked by your hand", (h or {}).get("title", ""), h)

    def test_his_tick_moves_the_count_on_the_painted_list_and_the_readout(self):
        b, a = self.o["before"], self.o["after"]
        self.assertTrue(self.o["ticked"], "PREMISE: no move row to tick: %r" % self.o)
        self.assertTrue(b and b["m"] >= 3 and b["n"] == 0, "PREMISE: %r" % b)
        self.assertEqual((a["n"], a["m"]), (1, b["m"]), a)
        self.assertEqual(self.o["painted"], "in place 1 of %d" % b["m"], self.o["painted"])
        self.assertEqual((self.o["audit"] or {}).get("n"), 1, "the readout does not carry it: %r" % self.o["audit"])


RED_PROOF = [
    {"why": "REG-3065 - the list never says how many copies are in place",
     "file": "bible.html",
     "find": "      + (_ip && _ip.m > 0 ? '<span class=\"vmv-inplace\" title=\"' + esc(_ip.say) + '\">in place ' + _ip.n + ' of ' + _ip.m + '</span>' : '')\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3065 - his tick is not counted in place",
     "file": "bible.html",
     "find": "      else if (t.status === 'moved-manual') ticked++;\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3065 - a throw-out or a drained row is counted among the copies with a home",
     "file": "bible.html",
     "find": "      if (!t || t.kind === 'throw' || t.status === 'closed') return;\n",
     "replace": "      if (!t) return;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3065 - the readout leaves it out",
     "file": "bible.html",
     "find": "    try { out.inPlace = (typeof window._vaultInPlace === 'function') ? window._vaultInPlace() : null; } catch (eIp) { out.inPlace = null; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
