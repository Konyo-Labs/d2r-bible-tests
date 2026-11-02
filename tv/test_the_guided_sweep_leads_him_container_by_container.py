# -*- coding: utf-8 -*-
"""REG-3113 (#202, his 2026-10-27 ruling and his Q11) - THE GUIDED SWEEP LEADS HIM CONTAINER BY CONTAINER, CAPPED HONESTLY, AND A
STEP CLOSES ONLY WHEN A SWEEP SEES ITS CONTAINER WHOLE.

REG-3105 made a container's full look its truth and parked everything less as a question; nothing led him to the
containers. MOVE TASKS now carries ONE guided step (window._vaultGuideSteps / _vaultGuideHtml, in the make rows' own form)
per open question and per container with no full look yet - each mule he has made, by its name, and each shared page; a
mule the board made and he has not is its make row's first - merged when they are the same container: "Open <holder> ·
<container> and hover every item", with the cells never named, the frame and the question's answers.
  * order: the steps with an open QUESTION first, then the oldest look (never seen whole is the oldest), then the most cells
    never named;
  * the list is CAPPED so it never buries the moves: every question is drawn, then never-seen containers up to 5 steps in
    all, then one counted line - "and N more containers never seen whole"; the cut never hides a question;
  * the head says "seen whole N of M" over every container in scope, and once what the scope leaves out;
  * a step closes itself: it is drawn from the full-look store each paint, so the sweep that completes the container
    removes it; a shadow draws the steps read only.
Driven on the whole page in node through vaultAccumApply with payloads of the console's shape (fixture names, sessions and
frames - never his data). REG-3114 (his tick) has its own law. RED_PROOF below.
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

S1, S2, S3 = "s_1790000000001_00001", "s_1790000000002_00002", "s_1790000000003_00003"


def _look(sid, frame, loc, occupied, page=None):
    return {"session": sid, "frame": frame, "capturedAt": int(frame[2:15]), "location": loc, "page": page,
            "grid": [10, 10], "occupied": occupied, "why": None}


def _row(name, sid, cells):
    return {"name": name, "witnesses": [{"session": sid, "frame": "f_17900000%05d.jpg" % (i + 1), "conf": 0.9, "lane": "stash",
                                         "cell": "stash:c%dr%d" % (c, r)} for i, (c, r) in enumerate(cells)]}


HC = [[0, 0], [1, 0], [0, 1], [1, 1]]
SWEEP1 = {"items": [_row("Harlequin Crest", S1, [(0, 0)]), _row("Annihilus", S2, [(4, 4)])], "unsure": [],
          "containers": [_look(S1, "f_1790000000100.jpg", "stash", HC),                       # UNI-ARMOR seen whole
                         _look(S2, "f_1790000000200.jpg", "stash", [[4, 4], [7, 7]]),           # SETS-REST: c7r7 never named
                         _look(S2, "f_1790000000300.jpg", "shared", [[2, 2]])]}                 # a shared page: which one?
SWEEP2 = {"items": [_row("Harlequin Crest", S1, [(0, 0)])], "unsure": [],
          "containers": [_look(S1, "f_1790000000500.jpg", "stash", HC + [[9, 9]]),             # UNI-ARMOR again: c9r9 unnamed
                         _look(S3, "f_1790000000600.jpg", "stash", [])]}                        # RUNEWORDS: empty, seen whole

QS = ["s_17900000001%d_0001%d" % (i, i) for i in range(5)]
QM = ["SOCKETED", "WIP", "GRAIL-DUPES", "UNI-SMALL", "MAGIC & RARE"]
SWEEPQ = {"items": [], "unsure": [], "containers": [_look(QS[i], "f_17900000007%02d.jpg" % i, "stash", [[3, 3]]) for i in range(5)]}

PRE = "localStorage.setItem('d2r_ownerClaim', '*');\nlocalStorage.setItem('d2r_vaultAutoIntake', 'on');\n"
BODY = r"""
(function(){
var W = window, A = __A__, B = __B__, Q = __Q__;
var m = {}; m[__S1__] = [{ from: null, character: 'UNI-ARMOR' }]; m[__S2__] = [{ from: null, character: 'SETS-REST' }]; m[__S3__] = [{ from: null, character: 'RUNEWORDS' }];
__QS__.forEach(function(s, i){ m[s] = [{ from: null, character: __QM__[i] }]; });
W._cbLearnedTakeForLaw({ ok: true, chars: [], sessions: m });
function snap(){ var s = W._vaultGuideSteps() || [], h = W._vaultGuideHtml();
  return { keys: s.map(function(x){ return x.key; }), kinds: s.map(function(x){ return x.ask ? x.ask.kind : 'never'; }), html: h,
           drawn: (h.match(/<li class="vgs-line vtk-look" data-container="[^"]*"/g) || []).map(function(t){ return t.split('data-container="')[1].slice(0, -1).replace(/&amp;/g, '&'); }),
           more: (/data-more="(\d+)"/.exec(h) || [])[1] || null }; }
OUT.before = snap();
W.vaultAccumApply(A);
OUT.after1 = snap();
W.vaultAccumApply(B);
OUT.after2 = snap();
W.vaultAccumApply(Q);
OUT.afterQ = snap();
try { W._vaultMovePaint(); } catch (e) { OUT.paintErr = String(e); }
OUT.paint = String((document.getElementById('vault-move-list') || {}).innerHTML || '');
W._tvdShadow = true;
OUT.shadowHtml = W._vaultGuideHtml();
})();
""".replace("__A__", json.dumps(SWEEP1)).replace("__B__", json.dumps(SWEEP2)).replace("__Q__", json.dumps(SWEEPQ)) \
   .replace("__QS__", json.dumps(QS)).replace("__QM__", json.dumps(QM)) \
   .replace("__S1__", json.dumps(S1)).replace("__S2__", json.dumps(S2)).replace("__S3__", json.dumps(S3))


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class TheGuidedSweepLeadsHimContainerByContainer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=PRE, timeout=300)

    def test_every_container_never_seen_whole_is_a_step_capped_and_counted(self):
        b = self.o["before"]
        self.assertIn("stash|uni-armor", b["keys"])
        self.assertIn("shared|shared stash|0", b["keys"])
        self.assertEqual(set(b["kinds"]), {"never"})
        self.assertNotIn("stash|charms", b["keys"], "a mule he has not made yet was given a step before its make row")
        n = len(b["keys"])
        self.assertIn('data-sec="look"', b["html"])
        self.assertIn("seen whole 0 of %d" % n, b["html"])
        self.assertIn("Mule 2+ characters and your own characters", b["html"], "the head does not say what the scope leaves out")
        self.assertEqual(len(b["drawn"]), 5, "the list is not capped at 5: %r" % b["drawn"])
        self.assertEqual((b["more"], "and %d more containers never seen whole" % (n - 5) in b["html"]), (str(n - 5), True),
                         "the cut is not counted: %r" % b["more"])

    def test_a_sweep_that_sees_a_container_whole_closes_its_step(self):
        a = self.o["after1"]
        self.assertNotIn("stash|uni-armor", a["keys"], "UNI-ARMOR was seen whole and its step stayed")
        self.assertIn("seen whole 1 of %d" % len(self.o["before"]["keys"]), a["html"])
        self.assertNotIn("stash|runewords", self.o["after2"]["keys"], "RUNEWORDS was seen whole (empty) and its step stayed")

    def test_questions_first_with_their_evidence(self):
        a = self.o["after1"]
        self.assertEqual(a["kinds"][:2], ["never-hovered", "page-unknown"], "the questions are not first: %r" % a["kinds"][:4])
        self.assertEqual(a["keys"][0], "stash|sets-rest")
        self.assertIn("1 cell never named: c7r7", a["html"])
        self.assertIn("frame f_1790000000200.jpg", a["html"])
        self.assertIn(">Page 3</button>", a["html"])
        x = self.o["after2"]
        self.assertIn("stash|uni-armor", x["keys"], "UNI-ARMOR's newer question is not a step")
        self.assertLess(x["keys"].index("stash|sets-rest"), x["keys"].index("stash|uni-armor"),
                        "a container never seen whole is not ahead of one seen whole before")
        qpos = [i for i, k in enumerate(x["kinds"]) if k != "never"]
        npos = [i for i, k in enumerate(x["kinds"]) if k == "never"]
        self.assertTrue(qpos and npos and max(qpos) < min(npos),
                        "a question (UNI-ARMOR's, seen whole before) sorts after a never-seen step: %r" % list(zip(x["keys"], x["kinds"]))[:8])

    def test_the_cut_never_hides_a_question(self):
        q = self.o["afterQ"]
        asked = [k for k, kind in zip(q["keys"], q["kinds"]) if kind != "never"]
        self.assertGreater(len(asked), 5, "PREMISE: fewer than 6 questions are open: %r" % asked)
        self.assertEqual(q["drawn"], asked, "a question was cut, or a never-seen step drawn ahead of one")
        never = len(q["keys"]) - len(asked)
        self.assertEqual(q["more"], str(never), "the cut count is not the never-seen steps it hides")

    def test_move_tasks_draws_the_steps(self):
        self.assertIn('data-sec="look"', self.o["paint"], "MOVE TASKS does not draw the guided steps: %r" % self.o.get("paintErr"))

    def test_a_shadow_draws_read_only(self):
        h = self.o["shadowHtml"]
        self.assertIn('data-sec="look"', h)
        self.assertNotIn(">Page 1</button>", h, "a shadow offered an answer")
        self.assertNotIn(">Clear</button>", h)


RED_PROOF = [
    {"why": "REG-3113 - a container seen whole keeps its step",
     "file": "bible.html",
     "find": "    _guideContainers().forEach(function(c){ var s = step(c); if (s.last) s.drop = true; });",
     "replace": "    _guideContainers().forEach(function(c){ var s = step(c); });",
     "matches": 1, "needs": "node"},
    {"why": "REG-3113 - the steps are not in his order (fewest unnamed cells first)",
     "file": "bible.html",
     "find": "(b.unnamed - a.unnamed)",
     "replace": "(a.unnamed - b.unnamed)",
     "matches": 1, "needs": "node"},
    {"why": "REG-3113 - a mule he has not made yet is given a step",
     "file": "bible.html",
     "find": "      if (!m || !m.name || m.id === 'shared' || pending[m.id]) return;",
     "replace": "      if (!m || !m.name || m.id === 'shared') return;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3113 - MOVE TASKS does not draw the guided steps",
     "file": "bible.html",
     "find": "      if (host && typeof window._vaultGuideHtml === 'function') host.innerHTML += window._vaultGuideHtml();   /* REG-3113 the guided sweep */\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3113 - the list is not capped (dozens of rows bury the moves)",
     "file": "bible.html",
     "find": "  var GUIDE_CAP = 5;\n",
     "replace": "  var GUIDE_CAP = 500;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-3113 - the cut is silent (no 'N more' line)",
     "file": "bible.html",
     "find": "    if (more > 0) h += '<li class=\"vtk-line vtk-more\"",
     "replace": "    if (false) h += '<li class=\"vtk-line vtk-more\"",
     "matches": 1, "needs": "node"},
    {"why": "REG-3113 - the cut can hide a question (questions capped with the rest)",
     "file": "bible.html",
     "find": "    var shown = asked.concat(never.slice(0, Math.max(0, GUIDE_CAP - asked.length))), more = steps.length - shown.length;",
     "replace": "    var shown = asked.concat(never).slice(0, GUIDE_CAP), more = steps.length - shown.length;",
     "matches": 1, "needs": "node"},
    {"why": "REG-3113 - a question does not sort ahead of the never-seen steps",
     "file": "bible.html",
     "find": "      return ((a.ask ? 0 : 1) - (b.ask ? 0 : 1)) || ",
     "replace": "      return ",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
