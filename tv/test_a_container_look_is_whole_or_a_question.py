# -*- coding: utf-8 -*-
"""REG-3105 (#158 P4, the intake design's guided sweep; his calls A and B) - A CONTAINER'S LOOK IS A FULL LOOK ONLY WHEN
EVERY TAKEN CELL IS NAMED EXACTLY ONCE; ANYTHING LESS IS A QUESTION TO HIM WITH THE EVIDENCE.

The sweep carries each container's own cells (REG-3104). The board assembles (his call A: it owns the sizes and the
receiver): window._vaultFullLookFrom lays the session's named reads (each its own frame, over the floor when scored) on the
taken cells with _itemCells' sizes - a read may sit anywhere inside its footprint, two reads of one name inside one
footprint are one item - and stamps _vaultFullLook only when exactly one layout explains every taken cell once and no read
sits on an empty cell. Anything less is never a look; it is a question in MOVE TASKS, stored with its evidence:
  * a shared page's number is never read (his call B): "which shared page was this?" - his answer stamps it;
  * a cell no read named, a read on an empty cell, two names on one cell, an item with no fixed size, an unread panel -
    each said as what it is, with the cells and the frame;
  * the gate holds it all when AUTO INTAKE is off; a shadow writes nothing and draws the owner's questions read only.
Driven on the whole page in node through vaultAccumApply with a payload of the console's shape (fixture names, sessions
and frames - never his data). RED_PROOF below.
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

S = "s_1790000000001_00001"


def _look(loc, occupied, frame="f_1790000000900.jpg", page=None, why=None):
    return {"session": S, "frame": frame, "capturedAt": int(frame[2:15]) if frame[2:15].isdigit() else None,
            "location": loc, "page": page, "grid": [10, 4] if loc == "inventory" else [10, 10],
            "occupied": occupied, "why": why}


def _row(name, cells, loc="stash"):
    return {"name": name, "witnesses": [{"session": S, "frame": "f_17900000005%02d.jpg" % i, "conf": 0.9, "lane": "stash",
                                         "cell": "%s:c%dr%d" % (loc, c, r)} for i, (c, r) in enumerate(cells)]}


def _rect(x, y, w, h):
    return [[x + dx, y + dy] for dy in range(h) for dx in range(w)]


# a personal stash: Harlequin Crest (2x2) at c0r0 hovered twice, Gheed's Fortune (1x3) at c5r2, Mara's (1x1) at c9r9
WHOLE = _look("stash", _rect(0, 0, 2, 2) + _rect(5, 2, 1, 3) + [[9, 9]])
ROWS = [_row("Harlequin Crest", [(1, 1), (0, 0)]), _row("Gheed's Fortune", [(5, 3)]), _row("Mara's Kaleidoscope", [(9, 9)])]
CASES = {
    "whole": (WHOLE, ROWS),
    "never": (_look("stash", _rect(0, 0, 2, 2) + [[7, 7]], frame="f_1790000000901.jpg"), [_row("Harlequin Crest", [(0, 0)])]),
    "empty": (_look("stash", _rect(0, 0, 2, 2), frame="f_1790000000902.jpg"), [_row("Harlequin Crest", [(0, 0)]), _row("Annihilus", [(6, 6)])]),
    "twoNames": (_look("stash", _rect(0, 0, 2, 2), frame="f_1790000000903.jpg"), [_row("Harlequin Crest", [(0, 0)]), _row("Vampire Gaze", [(1, 1)])]),
    "unsized": (_look("stash", [[3, 3]], frame="f_1790000000904.jpg"), [_row("Stone of Jordan", [(3, 3)])]),
    "unread": (_look("stash", None, frame="f_1790000000905.jpg", why="the cells of this panel could not be read on this frame - UNKNOWN"), ROWS),
    "shared": (_look("shared", [[2, 2]], frame="f_1790000000906.jpg"), [_row("Annihilus", [(2, 2)])]),
    "tab": (_look(None, [[4, 4]], frame="f_1790000000907.jpg"), [_row("Annihilus", [(4, 4)])]),
}

PRE = ("localStorage.setItem('d2r_ownerClaim', '*');\n"
       "localStorage.setItem('d2r_vaultAutoIntake', %s);\n")
BODY = r"""
(function(){
var W = window, C = __CASES__, SID = __S__;
W._cbLearnedTakeForLaw({ ok: true, chars: [], sessions: (function(){ var m = {}; m[SID] = [{ from: null, character: 'KonyoLock' }]; return m; })() });
function apply(name){ var c = C[name]; var r = W.vaultAccumApply({ items: c[1], unsure: [], containers: [c[0]] }); return r && r.fullLooks; }
OUT.res = {};
Object.keys(C).forEach(function(k){ OUT.res[k] = apply(k); });
var asks = W._vaultFullLookAsks() || {};
OUT.asks = {}; Object.keys(asks).forEach(function(id){ var q = asks[id]; OUT.asks[q.frame] = { kind: q.kind, why: q.why, cells: q.cells, holder: (q.container || {}).holder }; });
OUT.looks = JSON.parse(localStorage.getItem('d2r_vaultFullLooks') || '{}');
OUT.html = W._vaultFullLookAsksHtml();
/* his answer: the shared question, page 2 */
var shId = Object.keys(asks).filter(function(id){ return asks[id].kind === 'page-unknown'; })[0];
OUT.answer = shId ? W._vaultFullLookAnswer(shId, 1) : null;
OUT.looksAfter = Object.keys(JSON.parse(localStorage.getItem('d2r_vaultFullLooks') || '{}'));
OUT.asksAfter = Object.keys(W._vaultFullLookAsks() || {}).length;
/* a shadow: draws the questions with no answer, writes nothing */
W._tvdShadow = true;
OUT.shadowHtml = W._vaultFullLookAsksHtml();
var before = localStorage.getItem('d2r_vaultFullLookAsks');
OUT.shadowApply = W._vaultFullLooksApply({ items: C.never[1], containers: [Object.assign({}, C.never[0], { frame: 'f_1790000000999.jpg' })] });
OUT.shadowClear = W._vaultFullLookClear(Object.keys(asks)[0]);
OUT.shadowAnswer = W._vaultFullLookAnswer(Object.keys(asks)[0], 1);
OUT.shadowWrote = localStorage.getItem('d2r_vaultFullLookAsks') !== before;
OUT.forked = !!(W._LP_FORKED && W._LP_FORKED.has('d2r_vaultFullLookAsks'));
})();
"""


def _run(auto):
    return VPN.run(BODY.replace("__CASES__", json.dumps(CASES)).replace("__S__", json.dumps(S)), prelude=PRE % json.dumps(auto), timeout=300)


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AContainerLookIsWholeOrAQuestion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.on = _run("on")
        cls.off = _run("off")

    def test_every_taken_cell_named_once_is_a_full_look(self):
        r = self.on["res"]["whole"]
        self.assertEqual((r["stamped"], r["asked"]), (1, 0), r)
        st = self.on["looks"].get("stash|KonyoLock")
        self.assertTrue(st, "no full look was stamped for KonyoLock's stash: %r" % self.on["looks"])
        self.assertEqual((st["items"], st["empty"], st["frame"]), (3, 100 - 4 - 3 - 1, "f_1790000000900.jpg"), st)

    def test_anything_less_is_a_question_with_its_evidence(self):
        a = self.on["asks"]
        want = {"f_1790000000901.jpg": "never-hovered", "f_1790000000902.jpg": "conflict", "f_1790000000903.jpg": "conflict",
                "f_1790000000904.jpg": "size-unknown", "f_1790000000905.jpg": "occupancy-unknown",
                "f_1790000000907.jpg": "tab-unknown"}
        got = {f: (a.get(f) or {}).get("kind") for f in want}
        self.assertEqual(got, want, a)
        self.assertEqual(a["f_1790000000901.jpg"]["cells"], ["c7r7"], "the never-hovered cell was not named")
        self.assertEqual(a["f_1790000000901.jpg"]["holder"], "KonyoLock")
        self.assertIn("Annihilus at c6r6", a["f_1790000000902.jpg"]["why"])

    def test_a_shared_page_is_asked_and_his_answer_stamps_it(self):
        self.assertEqual(self.on["asks"]["f_1790000000906.jpg"]["kind"], "page-unknown")
        self.assertIn("which shared page was this?", self.on["asks"]["f_1790000000906.jpg"]["why"])
        self.assertNotIn("shared|SHARED STASH|p1", self.on["looks"], "a shared page was stamped before he named it")
        self.assertTrue(self.on["answer"] and self.on["answer"].get("stamped"), "his answer did not stamp: %r" % self.on["answer"])
        self.assertIn("shared|SHARED STASH|p1", self.on["looksAfter"])
        self.assertIn("Page 2</button>", self.on["html"], "the question offers no page to answer")

    def test_auto_intake_off_assembles_and_asks_nothing(self):
        for k, r in self.off["res"].items():
            self.assertEqual((r.get("stamped"), r.get("asked")), (0, 0), "%s: %r" % (k, r))
            self.assertIn("AUTO INTAKE", r.get("held") or "", r)
        self.assertEqual(self.off["looks"], {})

    def test_a_shadow_draws_read_only_and_writes_nothing(self):
        o = self.on
        self.assertIn("FULL LOOK QUESTIONS", o["shadowHtml"])
        self.assertNotIn("Page 1</button>", o["shadowHtml"], "a shadow offered an answer")
        self.assertNotIn(">Clear</button>", o["shadowHtml"])
        self.assertTrue(o["shadowApply"].get("held"), "a shadow assembled a look: %r" % o["shadowApply"])
        for k in ("shadowClear", "shadowAnswer"):
            self.assertFalse(o[k].get("ok"), "%s: %r" % (k, o[k]))
            self.assertIn("shadow", o[k].get("why") or "", "%s was refused for another reason: %r" % (k, o[k]))
        self.assertFalse(o["shadowWrote"], "a shadow wrote the question store")
        self.assertTrue(o["forked"], "d2r_vaultFullLookAsks is not forked per profile")


RED_PROOF = [
    {"why": "REG-3105 - a container with a cell no read named is stamped whole",
     "file": "bible.html",
     "find": "    if (!full.length){\n      var left = sols[0].left.map(",
     "replace": "    if (!full.length) full = sols;\n    if (false){\n      var left = sols[0].left.map(",
     "matches": 1, "needs": "node"},
    {"why": "REG-3105 - a read on an empty cell is dropped instead of asked",
     "file": "bible.html",
     "find": "    var misfit = rds.filter(function(rd, i){ return !cand[i].length; });\n",
     "replace": "    var misfit = [];\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3105 - a shared page with no number is guessed as page 1",
     "file": "bible.html",
     "find": "    var page = (look.page == null || look.page === '') ? null : +look.page;\n",
     "replace": "    var page = (look.page == null || look.page === '') ? 0 : +look.page;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3105 - an unread panel's cells are counted empty",
     "file": "bible.html",
     "find": "    if (!Array.isArray(look.occupied))\n      return no('occupancy-unknown',",
     "replace": "    if (!Array.isArray(look.occupied)) look = Object.assign({}, look, { occupied: [] });\n    if (false)\n      return no('occupancy-unknown',",
     "matches": 1, "needs": "node"},
    {"why": "REG-3105 - AUTO INTAKE off still assembles a look",
     "file": "bible.html",
     "find": "    if (gate) { out.held = gate.why || gate.refused; return out; }\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3105 - the sweep apply never asks for a full look",
     "file": "bible.html",
     "find": "      try { out.fullLooks = (typeof window._vaultFullLooksApply === 'function') ? window._vaultFullLooksApply(p)\n",
     "replace": "      try { out.fullLooks = false ? window._vaultFullLooksApply(p)\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3105 - a shadow clears his question (its door does not refuse it)",
     "file": "bible.html",
     "find": "    if (_flShadow()) return { ok: false, why: 'a shadow clears nothing' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3105 - a shadow answers his question",
     "file": "bible.html",
     "find": "    if (_flShadow()) return { ok: false, why: 'a shadow answers nothing - it is their console, shown read only' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
