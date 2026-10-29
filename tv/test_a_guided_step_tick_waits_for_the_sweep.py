# -*- coding: utf-8 -*-
"""REG-3114 (#202) - HIS TICK ON A GUIDED STEP IS NEVER THE PROOF: IT WAITS FOR THE SWEEP THAT SEES THE CONTAINER WHOLE.

A guided step (REG-3113) closes only when a sweep's containers[] completes its container - never by a click alone. His
tick (window._vaultGuideDone) records that he hovered it, as a 'guide-done' row on that container in the question store
REG-3105 keeps (no new store); the step stays, checked, and says "you said done <time> - waiting for the next sweep to see
it whole" - and it is never cut by REG-3113's cap (hidden, it would read as closed). A full look of that container clears the
tick with the step (REG-3105's own clearing of that container's older
rows). A step whose container is not named yet (a shared page with no number) cannot be ticked - its question is answered
first. A shadow's tick refuses (REG-3095's guard form). Driven on the whole page in node, fixture sessions and frames.
RED_PROOF below.
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

S3, S4 = "s_1790000000003_00003", "s_1790000000004_00004"
SHARED = {"items": [], "unsure": [], "containers": [{"session": S4, "frame": "f_1790000000300.jpg", "capturedAt": 1790000000300,
                                                     "location": "shared", "page": None, "grid": [10, 10], "occupied": [[2, 2]], "why": None}]}
WHOLE = {"items": [], "unsure": [], "containers": [{"session": S3, "frame": "f_1790000000600.jpg", "capturedAt": 1790000000600,
                                                    "location": "stash", "page": None, "grid": [10, 10], "occupied": [], "why": None}]}

PRE = "localStorage.setItem('d2r_ownerClaim', '*');\nlocalStorage.setItem('d2r_vaultAutoIntake', 'on');\n"
BODY = r"""
(function(){
var W = window, SH = __SH__, WH = __WH__;
var m = {}; m[__S3__] = [{ from: null, character: 'RUNEWORDS' }];
W._cbLearnedTakeForLaw({ ok: true, chars: [], sessions: m });
function row(key){ var h = W._vaultGuideHtml(), i = h.indexOf('data-container="' + key + '"');
  return i < 0 ? null : h.slice(h.lastIndexOf('<li', i), h.indexOf('</li>', i) + 5); }
function asks(){ return Object.keys(W._vaultFullLookAsks() || {}); }
OUT.tick = W._vaultGuideDone('stash|runewords');
OUT.tickedRow = row('stash|runewords');
OUT.stepsAfterTick = (W._vaultGuideSteps() || []).map(function(s){ return s.key; });
OUT.asksAfterTick = asks();
W.vaultAccumApply(SH);
var shKey = asks().filter(function(id){ return id.indexOf('|shared|') > 0; })[0];
OUT.sharedTick = W._vaultGuideDone(shKey);
W.vaultAccumApply(WH);
OUT.stepsAfterSweep = (W._vaultGuideSteps() || []).map(function(s){ return s.key; });
OUT.asksAfterSweep = asks();
W._tvdShadow = true;
OUT.shadowRow = row('shared|shared stash|0');
OUT.shadowTick = W._vaultGuideDone('shared|shared stash|0');
})();
""".replace("__SH__", json.dumps(SHARED)).replace("__WH__", json.dumps(WHOLE)).replace("__S3__", json.dumps(S3))


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AGuidedStepTickWaitsForTheSweep(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.o = VPN.run(BODY, prelude=PRE, timeout=300)

    def test_his_tick_is_recorded_and_the_step_waits(self):
        t = self.o["tick"]
        self.assertTrue(t["ok"] and t["waiting"], t)
        self.assertIn("stash|runewords", self.o["stepsAfterTick"], "his tick alone closed the step")
        r = self.o["tickedRow"] or ""
        self.assertIn(" checked", r, "the ticked step is not drawn ticked: %r" % r)
        self.assertIn("waiting for the next sweep to see it whole", r)
        self.assertIn("guide|stash|runewords", self.o["asksAfterTick"])

    def test_the_sweep_that_sees_it_whole_closes_the_step_and_the_tick(self):
        self.assertNotIn("stash|runewords", self.o["stepsAfterSweep"], "the sweep saw RUNEWORDS whole and its step stayed")
        self.assertNotIn("guide|stash|runewords", self.o["asksAfterSweep"], "the tick outlived the full look that answered it")

    def test_a_step_with_no_container_named_cannot_be_ticked(self):
        st = self.o["sharedTick"]
        self.assertFalse(st["ok"], st)
        self.assertIn("answer its question first", st["why"])

    def test_a_shadows_tick_refuses(self):
        self.assertIn(" disabled", self.o["shadowRow"] or "", "a shadow's tick is live: %r" % self.o["shadowRow"])
        self.assertFalse(self.o["shadowTick"]["ok"])
        self.assertIn("shadow", self.o["shadowTick"]["why"])


RED_PROOF = [
    {"why": "REG-3114 - his tick closes the step by itself",
     "file": "bible.html",
     "find": "      if (q.kind === 'guide-done'){ if (known) step(c).done = q; return; }",
     "replace": "      if (q.kind === 'guide-done'){ if (known) { step(c).done = q; step(c).drop = true; } return; }",
     "matches": 1, "needs": "node"},
    {"why": "REG-3114 - a ticked step is cut by the cap and reads as closed",
     "file": "bible.html",
     "find": "    var asked = steps.filter(function(s){ return !!(s.ask || s.done); }), never = steps.filter(function(s){ return !(s.ask || s.done); });",
     "replace": "    var asked = steps.filter(function(s){ return !!s.ask; }), never = steps.filter(function(s){ return !s.ask; });",
     "matches": 1, "needs": "node"},
    {"why": "REG-3114 - a shadow ticks his step",
     "file": "bible.html",
     "find": "    if (_flShadow()) return { ok: false, why: 'a shadow ticks nothing - it is their console, shown read only' };\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-3114 - a step whose container is not named is ticked anyway",
     "file": "bible.html",
     "find": "    if (!c || !c.location || !c.holder || (c.location === 'shared' && c.page == null))\n      return { ok: false, why: 'that step names no container yet - answer its question first' };\n",
     "replace": "    if (!c) return { ok: false, why: 'that step names no container yet - answer its question first' };\n",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
