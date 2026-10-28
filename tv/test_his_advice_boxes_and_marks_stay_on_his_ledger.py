# -*- coding: utf-8 -*-
"""REG-2921 (#252) - HIS ADVICE BOXES AND HIS "YOURS" MARKS SPEAK TO HIM ON HIS LEDGER, AND TO WHOEVER PLAYS ANYWHERE ELSE.

His rule (2026-09-27): every personal surface is per-PC. Nine guide boxes in the markup open "For Konyo:" or "For Konyo
(Warlock):", the Caster craft carries a `konyo:` note ("Your craft, Konyo - ...") on three surfaces, and the same craft wears
"★ YOURS" on the workshop tile and the Forge's craft accordion (and sorts first in the Forge's craft tasks). Every PC got all
of it. On his ledger (the v2692 gate, `_seedsBelongHere`) nothing changes. Anywhere else a box reads "If you play a
Warlock:" or "Tip:", and his craft note and his star are not drawn.

Driven on the whole page in node (vault_page_node), three fixture worlds: HIS (claimed, ledger KonyoEndgame), OTHER
(claimed, another named ledger), GUEST (an unclaimed store). The markup's own text nodes are handed to the page's boot
walker through a tree-walker stand-in. RED_PROOF below.
"""
import html as _html
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

FOR_KONYO = re.compile(r"For Konyo")
CLAIM = "localStorage.setItem('d2r_ownerClaim', '*');"
WORLDS = {
    "his": CLAIM + "localStorage.setItem('d2r_ledgerName', 'KonyoEndgame');",
    "other": CLAIM + "localStorage.setItem('d2r_ledgerName', 'Deans-Own-Ledger');",
    "guest": "",
}
# the Forge's craft accordion lives inside the Forge's own scope; the law reaches it the way the page calls it
PATCHES = [("  function _craftAccHtml(ck, col){\n",
            "  window.__craftAccHtmlForLaw = function(a, b){ return _craftAccHtml(a, b); };\n  function _craftAccHtml(ck, col){\n", 1)]


def static_text_nodes():
    """The markup's text nodes that address him, as the browser's tree walker would hand them to the page. -> [str]"""
    s = io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8").read()
    for rx in (r"<script\b[^>]*>[\s\S]*?</script>", r"<style\b[^>]*>[\s\S]*?</style>", r"<!--[\s\S]*?-->",
               r"<textarea\b[^>]*>[\s\S]*?</textarea>"):
        s = re.sub(rx, "", s)
    return [_html.unescape(t) for t in re.split(r"<[^>]+>", s) if re.search(r"Konyo(?:lock|din|ress|ssin)|For Konyo", t, re.I)]


def prelude(world):
    nodes = [{"nodeValue": t, "parentNode": {"nodeName": "DIV"}} for t in static_text_nodes()]
    return (WORLDS[world] + "window.NodeFilter = window.NodeFilter || { SHOW_TEXT: 4 };"
            "window.__STATIC_NODES = %s;"
            "document.createTreeWalker = function(){ var i = -1, N = window.__STATIC_NODES;"
            " return { nextNode: function(){ i++; return i < N.length ? N[i] : null; } }; };" % json.dumps(nodes))


BODY = r"""
(function(){
var S = {}, ERR = [];
function tryit(k, f){ try { f(); } catch (e) { ERR.push(k + ': ' + String(e && e.message || e)); } }
function grab(id){ var e = document.getElementById(id); return e ? String(e.innerHTML || '') : ''; }
tryit('workshop', function(){ _craftSel = 'Caster'; renderCraftWorkshop(); S.workshop = grab('craft-workshop'); });
tryit('craftCard', function(){ S.craftCard = craftDetailHtml('Caster'); });
tryit('recipe', function(){ S.recipe = _extraCraftRecipeHtml('Caster Amulet', { rarity: 'crafted' }); });
tryit('acc', function(){ S.acc = window.__craftAccHtmlForLaw('Caster'); });
tryit('forge', function(){ var sc = window.forgeScan(); S.types = (sc.craftTypes || []).length;
  S.typeStars = (sc.craftTypes || []).filter(function(r){ return r && r.star; }).map(function(r){ return r.craft; }); });
OUT.S = S; OUT.ERR = ERR;
OUT.note = (CRAFTS.filter(function(c){ return c.key === 'Caster'; })[0] || {}).konyo || null;
OUT.static = (window.__STATIC_NODES || []).map(function(t){ return t.nodeValue; });
OUT.seeds = window._seedsBelongHere === true;
OUT.say = [window._charSay('For Konyo (Warlock): ring gambling is the only path'), window._charSay('For Konyo: Anni + Torch')];
})();
"""

_RUNS = {}


def page(world):
    if world not in _RUNS:
        _RUNS[world] = VPN.run(BODY, prelude=prelude(world), patches=PATCHES, timeout=600)
    return _RUNS[world]


def addressed(texts):
    return sum(len(FOR_KONYO.findall(t or "")) for t in texts)


@unittest.skipUnless(VPN.NODE, "node is absent on this machine - UNMEASURED here, never a pass")
class HisAdviceBoxesAndMarksStayOnHisLedger(unittest.TestCase):

    def test_the_premise_every_world_boots_and_every_surface_renders(self):
        for w in WORLDS:
            o = page(w)
            self.assertEqual(o["__boot"]["errors"], [], "%s: %r" % (w, o["__boot"]))
            self.assertEqual(o["ERR"], [], "%s: a surface threw: %r" % (w, o["ERR"]))
            for k in ("workshop", "craftCard", "recipe", "acc"):
                self.assertTrue(o["S"].get(k), "%s: %s rendered nothing" % (w, k))
            self.assertGreater(o["S"]["types"], 0, "%s: the Forge scan lists no craft types" % w)
        self.assertTrue(page("his")["seeds"], "PREMISE: the HIS world is not his ledger")
        self.assertFalse(page("other")["seeds"] or page("guest")["seeds"], "PREMISE: another world reads as his ledger")
        self.assertTrue(page("his")["note"], "PREMISE: the Caster craft carries no note of his - this law measures nothing")

    def test_his_ledger_keeps_his_boxes_note_and_star(self):
        o = page("his")
        self.assertEqual(o["static"], static_text_nodes(), "his ledger's markup text was rewritten")
        self.assertGreater(addressed(o["static"]), 0, "PREMISE: no box addresses him in the markup")
        for k in ("workshop", "craftCard", "recipe"):
            self.assertIn(o["note"], _html.unescape(o["S"][k]), "his craft note left his %s" % k)
        self.assertIn("★ YOURS", o["S"]["workshop"])
        self.assertIn("★ YOURS", o["S"]["acc"])
        self.assertEqual(o["S"]["typeStars"], ["Caster"])

    def test_no_other_board_is_addressed_as_him(self):
        for w in ("other", "guest"):
            o = page(w)
            got = o["static"]
            self.assertEqual(addressed(got), 0, "%s board's markup still says For Konyo: %r" % (
                w, [t for t in got if FOR_KONYO.search(t)][:3]))
            for k in ("workshop", "craftCard", "recipe", "acc"):
                self.assertNotIn("Konyo", _html.unescape(o["S"][k]), "%s board's %s names him" % (w, k))
                self.assertNotIn("★ YOURS", o["S"][k], "%s board's %s calls his craft its own" % (w, k))
            self.assertEqual(o["S"]["typeStars"], [], "%s board's Forge sorts his craft first as its own" % w)

    def test_a_box_reads_as_advice_to_whoever_plays(self):
        say = page("other")["say"]
        self.assertEqual(say[0], "If you play a Warlock: ring gambling is the only path")
        self.assertEqual(say[1], "Tip: Anni + Torch")
        self.assertEqual(page("his")["say"][1], "For Konyo: Anni + Torch")


RED_PROOF = [
    {"why": "REG-2921 - 'For Konyo (Class)' is left as it was on every board",
     "file": "bible.html",
     "find": "    .replace(/For Konyo \\(([A-Za-z]+)\\)/g, 'If you play a $1')\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2921 - 'For Konyo:' is left as it was on every board",
     "file": "bible.html",
     "find": "    .replace(/For Konyo\\b/g, 'Tip')\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2921 - the recipe row prints his craft note on every board",
     "file": "bible.html",
     "find": "(craft.konyo && window._seedsBelongHere === true ? ' <span class=\"ecr-konyo\">'",
     "replace": "(craft.konyo ? ' <span class=\"ecr-konyo\">'",
     "matches": 1, "needs": "node"},
    {"why": "REG-2921 - the workshop prints his craft note on every board",
     "file": "bible.html",
     "find": "      + (craft.konyo && window._seedsBelongHere === true ? '<div class=\"success\" style=\"margin:0 0 10px\">",
     "replace": "      + (craft.konyo ? '<div class=\"success\" style=\"margin:0 0 10px\">",
     "matches": 1, "needs": "node"},
    {"why": "REG-2921 - the craft card prints his craft note on every board",
     "file": "bible.html",
     "find": "    + (c.konyo && window._seedsBelongHere === true ? '<div class=\"success\" style=\"margin:0 0 14px\">",
     "replace": "    + (c.konyo ? '<div class=\"success\" style=\"margin:0 0 14px\">",
     "matches": 1, "needs": "node"},
    {"why": "REG-2921 - the workshop tile calls his craft YOURS on every board",
     "file": "bible.html",
     "find": "      + (c.star && window._seedsBelongHere === true ? '<span class=\"cw-tile-star\">★ YOURS</span>' : '')",
     "replace": "      + (c.star ? '<span class=\"cw-tile-star\">★ YOURS</span>' : '')",
     "matches": 1, "needs": "node"},
    {"why": "REG-2921 - the Forge's craft types mark his craft as the star on every board",
     "file": "bible.html",
     "find": "color:c.color, star:!!c.star && window._seedsBelongHere === true, tell:c.tell });",
     "replace": "color:c.color, star:!!c.star, tell:c.tell });",
     "matches": 1, "needs": "node"},
    {"why": "REG-2921 - the Forge's craft accordion calls his craft YOURS on every board",
     "file": "bible.html",
     "find": "+_fEsc(ck)+(c.star && window._seedsBelongHere === true?' <span class=\"cw-tile-star\">★ YOURS</span>':'')",
     "replace": "+_fEsc(ck)+(c.star?' <span class=\"cw-tile-star\">★ YOURS</span>':'')",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
