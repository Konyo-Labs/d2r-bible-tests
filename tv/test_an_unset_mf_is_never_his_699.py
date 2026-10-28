# -*- coding: utf-8 -*-
"""REG-2922 (#252) - AN MF NOBODY SET IS UNKNOWN, NEVER HIS 699; HIS TWO STARRED PRESETS ARE HIS ONLY ON HIS LEDGER.

His rule (2026-09-27): every personal surface is per-PC. `let mf = parseInt(LS.getItem('d2r_mf') || '699')` gave every PC
that never touched the slider HIS magic find (Konyolock's 699 loadout): the odds, the slider, the dock ("MF 699"), the
cockpit KPI ("699% MF") all said 699 on a board that is not his. And the presets 553 and 699 wore "⭐" and the "mine" look
with titles naming Konyolock on every PC.

On his ledger (the v2692 gate, `_seedsBelongHere`) nothing changes. Anywhere else an unset MF computes with 0 (the base odds)
and every place that shows "your MF" says it is not set - never 699, never a 0 that reads as measured. The presets keep
their values and lose the star, the look and his name. An MF someone set is theirs, shown as set, on any board.

Driven on the whole page in node (vault_page_node), four fixture worlds: HIS, OTHER (claimed, another ledger), GUEST
(unclaimed) and SET (OTHER with an MF of 300 saved). The two chips start as the markup draws them. RED_PROOF below.
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

CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');"
OTHER = CLAIM + "localStorage.setItem('d2r_ledgerName', 'Deans-Own-Ledger');"
WORLDS = {
    "his": CLAIM + "localStorage.setItem('d2r_ledgerName', 'KonyoEndgame');",
    "other": OTHER,
    "guest": "",
    "set": OTHER + "localStorage.setItem('d2r_mf', '300');",
}


def chips():
    """The two starred preset chips as the markup draws them -> {value: {cls, text, title}}"""
    s = io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r'<button class="([^"]*)" id="mf-preset-mine-(\d+)"[^>]*title="([^"]*)">([^<]*)</button>', s):
        out[m.group(2)] = {"cls": m.group(1).split(), "title": m.group(3), "text": m.group(4)}
    return out


def prelude(world):
    seed = "".join("(function(){ var c = document.getElementById('mf-preset-mine-%s'); %s c.textContent = %s; c.setAttribute('title', %s); })();"
                   % (v, "".join("c.classList.add(%s);" % json.dumps(k) for k in d["cls"]), json.dumps(d["text"]), json.dumps(d["title"]))
                   for v, d in chips().items())
    return WORLDS[world] + seed


BODY = r"""
(function(){
var ERR = [];
function tryit(k, f){ try { f(); } catch (e) { ERR.push(k + ': ' + String(e && e.message || e)); } }
function grab(id){ var e = document.getElementById(id); return e ? String(e.innerHTML || '') : ''; }
OUT.seeds = window._seedsBelongHere === true;
OUT.mf = mf;
OUT.unset = window._mfUnset();
tryit('eff', function(){ updateEffMF(); OUT.mfVal = document.getElementById('mf-val').textContent; OUT.slider = document.getElementById('mf').value; });
tryit('cockpit', function(){ window.renderSessionCockpit(); OUT.kpis = grab('sc-kpis'); OUT.intel = grab('sc-intel-body'); });
OUT.chips = {};
['553', '699'].forEach(function(v){ var c = document.getElementById('mf-preset-mine-' + v);
  OUT.chips[v] = c ? { mine: c.classList.contains('mf-preset-chip-mine'), text: c.textContent, title: c.getAttribute('title') } : null; });
tryit('cards', function(){ renderBossCards(); OUT.bossCards = grab('boss-cards');
  renderItemDetailCard('Harlequin Crest (Shako)'); OUT.item = grab('item-detail-panel'); });
tryit('wish', function(){ navigator.clipboard.writeText = function(t){ OUT.md = String(t); return Promise.resolve(); };
  wishlist.add('Harlequin Crest (Shako)'); window.exportWishlistAsMarkdown(); wishlist.delete('Harlequin Crest (Shako)'); });
tryit('persist', function(){ persist(); OUT.storedAfterPersist = LS.getItem('d2r_mf'); });
tryit('slide', function(){
  var s = document.getElementById('mf'); s.value = '250';
  try { s.oninput(); } catch (e) { OUT.slideErr = String(e && e.message || e); }
  OUT.afterSlide = { mf: mf, unset: window._mfUnset(), label: (updateEffMF(), document.getElementById('mf-val').textContent) };
  persist(); OUT.storedAfterSlide = LS.getItem('d2r_mf');
});
OUT.ERR = ERR;
})();
"""

_RUNS = {}


def page(world):
    if world not in _RUNS:
        _RUNS[world] = VPN.run(BODY, prelude=prelude(world), timeout=600)
    return _RUNS[world]


def mf_kpi(kpis):
    """the cockpit's MF tile -> its <b> value, or None"""
    m = re.search(r'<div class="sc-kpi"><b>([^<]*)</b><span>MF[^<]*</span></div>', kpis or "")
    return m.group(1) if m else None


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class AnUnsetMfIsNeverHis699(unittest.TestCase):

    def test_the_premise_every_world_boots_and_draws_its_mf(self):
        self.assertEqual(sorted(chips()), ["553", "699"], "PREMISE: the markup's starred preset chips moved: %r" % chips())
        for w in WORLDS:
            o = page(w)
            self.assertEqual(o["__boot"]["errors"], [], "%s: %r" % (w, o["__boot"]))
            self.assertEqual(o["ERR"], [], "%s: %r" % (w, o["ERR"]))
            self.assertIsNotNone(mf_kpi(o["kpis"]), "%s: the cockpit drew no MF tile: %r" % (w, (o["kpis"] or "")[:300]))
            self.assertIn("MF <b>", o["intel"] or "", "%s: the cockpit's dock line was not drawn" % w)
        self.assertTrue(page("his")["seeds"])
        self.assertFalse(page("other")["seeds"] or page("guest")["seeds"] or page("set")["seeds"])

    def test_his_ledger_keeps_699_and_his_presets(self):
        o = page("his")
        self.assertEqual((o["mf"], o["unset"], o["mfVal"], str(o["slider"])), (699, False, "699%", "699"))
        self.assertEqual(mf_kpi(o["kpis"]), "699%")
        self.assertIn("MF <b>699</b>", o["intel"])
        for v, d in chips().items():
            self.assertTrue(o["chips"][v]["mine"], "his ledger lost the mine look on %s" % v)
            self.assertEqual((o["chips"][v]["text"], o["chips"][v]["title"]), (d["text"], d["title"]))

    def test_an_unset_mf_off_his_ledger_is_unknown_never_699(self):
        for w in ("other", "guest"):
            o = page(w)
            self.assertEqual(o["mf"], 0, "%s board computes with MF %r it never set" % (w, o["mf"]))
            self.assertTrue(o["unset"], w)
            self.assertEqual(o["mfVal"], "not set", "%s board's slider label: %r" % (w, o["mfVal"]))
            self.assertEqual(str(o["slider"]), "0", w)
            self.assertEqual(mf_kpi(o["kpis"]), "?", "%s board's MF tile: %r" % (w, mf_kpi(o["kpis"])))
            self.assertIn("MF not set", o["kpis"])
            self.assertIn("MF <b>not set</b>", o["intel"], "%s board's dock line: %r" % (w, (o["intel"] or "")[:400]))
            self.assertNotIn("699", o["kpis"] + o["intel"] + o["mfVal"])

    def test_every_sentence_that_states_the_mf_says_it_is_not_set(self):
        for w in ("other", "guest"):
            o = page(w)
            self.assertIn("(your MF: not set)", o["bossCards"], "%s board's boss cards claim an MF it never set" % w)
            self.assertIn("@ base odds (MF not set)", o["item"], "%s board's item card states an MF it never set" % w)
            self.assertNotIn("@ 0% MF", o["item"] + o["bossCards"])
            self.assertIn("**MF**: not set", o["md"], "%s board's wishlist export states an MF it never set" % w)
        h = page("his")
        self.assertIn("(your MF: 699%)", h["bossCards"])
        self.assertIn("@ 699% MF", h["item"])
        self.assertIn("**MF**: 699%", h["md"])
        self.assertIn("@ 300% MF", page("set")["item"])

    def test_a_save_of_anything_else_never_turns_unset_into_a_measured_0(self):
        for w in ("other", "guest"):
            self.assertIsNone(page(w)["storedAfterPersist"],
                              "%s board: one persist() wrote MF %r it never picked - the next load shows it as set"
                              % (w, page(w)["storedAfterPersist"]))
        self.assertEqual(page("his")["storedAfterPersist"], "699")

    def test_moving_the_slider_is_a_choice_on_any_board(self):
        for w in ("other", "guest"):
            a = page(w)["afterSlide"]
            self.assertEqual((a["mf"], a["unset"], a["label"]), (250, False, "250%"), "%s board: %r" % (w, a))
            self.assertEqual(page(w)["storedAfterSlide"], "250", w)

    def test_an_mf_this_pc_set_is_shown_as_set(self):
        o = page("set")
        self.assertEqual((o["mf"], o["unset"], o["mfVal"]), (300, False, "300%"))
        self.assertEqual(mf_kpi(o["kpis"]), "300%")

    def test_his_starred_presets_are_plain_presets_elsewhere(self):
        for w in ("other", "guest"):
            for v in ("553", "699"):
                c = page(w)["chips"][v]
                self.assertFalse(c["mine"], "%s board: chip %s keeps his look" % (w, v))
                self.assertEqual(c["text"], v, "%s board: chip %s still reads %r" % (w, v, c["text"]))
                self.assertNotIn("Konyo", c["title"], "%s board: chip %s still names him: %r" % (w, v, c["title"]))


RED_PROOF = [
    {"why": "REG-2922 - an MF nobody set is his 699 on every board again",
     "file": "bible.html",
     "find": "let mf = parseInt(LS.getItem('d2r_mf') || (window._seedsBelongHere === true ? '699' : '0'));\n",
     "replace": "let mf = parseInt(LS.getItem('d2r_mf') || '699');\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - an unset MF is never reported as unset",
     "file": "bible.html",
     "find": "window._mfUnset = function(){ return !_mfChosen; };\n",
     "replace": "window._mfUnset = function(){ return false; };\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - an '@ N% MF' sentence states the unset 0 as a setting",
     "file": "bible.html",
     "find": "window._mfAtSay = function(){ return _mfChosen ? mf + '% MF' : 'base odds (MF not set)'; };",
     "replace": "window._mfAtSay = function(){ return mf + '% MF'; };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - 'your MF: N%' states the unset 0 as his setting",
     "file": "bible.html",
     "find": "window._mfPctSay = function(){ return _mfChosen ? mf + '%' : 'not set'; };",
     "replace": "window._mfPctSay = function(){ return mf + '%'; };",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - the wishlist export states the unset 0 as the MF",
     "file": "bible.html",
     "find": "  md += `**MF**: ${window._mfUnset() ? 'not set' : mf + '%'} · **Items**:",
     "replace": "  md += `**MF**: ${mf}% · **Items**:",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - every persist() writes the unset 0, so the next load reads it as picked",
     "file": "bible.html",
     "find": "  if (_mfChosen) LS.setItem('d2r_mf', mf);",
     "replace": "  LS.setItem('d2r_mf', mf);",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - moving the slider is not counted as a choice",
     "file": "bible.html",
     "find": "mf = parseInt($(\"mf\").value); _mfChosen = true; persistSoon();",
     "replace": "mf = parseInt($(\"mf\").value); persistSoon();",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - the slider label prints an unset MF as a number",
     "file": "bible.html",
     "find": "  $(\"mf-val\").textContent = window._mfUnset() ? 'not set' : mf + \"%\";",
     "replace": "  $(\"mf-val\").textContent = mf + \"%\";",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - the cockpit's MF tile prints an unset MF as a number",
     "file": "bible.html",
     "find": "    try { var _mfU = !!(window._mfUnset && window._mfUnset());",
     "replace": "    try { var _mfU = false;",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - the cockpit's dock line prints an unset MF as a number",
     "file": "bible.html",
     "find": "        var mfV = (window._mfUnset && window._mfUnset()) ? 'not set' : ",
     "replace": "        var mfV = ",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - his starred presets keep his look on every board",
     "file": "bible.html",
     "find": "window._mfPresetsUnmark = function(){\n  if (window._seedsBelongHere === true) return 0;\n",
     "replace": "window._mfPresetsUnmark = function(){\n  return 0;\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2922 - the presets are never unmarked at boot",
     "file": "bible.html",
     "find": "if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ window._mfPresetsUnmark(); });\n",
     "replace": "if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function(){ });\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
