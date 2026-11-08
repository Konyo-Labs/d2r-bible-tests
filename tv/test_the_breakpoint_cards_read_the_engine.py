# -*- coding: utf-8 -*-
"""v3885 (#134, his DESIGN C 11-08 13:17 + "15 frames. +9% more reaches the next step." 13:18) - THE CHARACTER BUILD SCREEN'S
BREAKPOINT CARDS READ THE ENGINE, AND THE RAIL, THE TIER AND THE LINE ARE ONE ANSWER.

His words via GrokBot (#230 6720814186 / 6720826884): the left column becomes a BREAKPOINTS panel of gauge-rail cards (FCR,
FHR, IAS, FBR + Attack Rating); each card computes "<N> frames. +<X>% more reaches the next step." live from the build's real
stat total, "N frames. Top breakpoint." at the top tier, UNKNOWN with what is missing - never a placeholder; the rail marker
and the tier label use the same computed values. His examples: Paladin 105% FCR -> "10 frames. +20% more reaches the next
step." (9 frames at 125%). Stash, Loot Filter and Strengths and Weaknesses leave the screen; Primary Skills and Mercenary go
under Stats.

Runs the page's own card code (_cbBpTiers, _cbBpCard) and the engine's own line (_ceBpSay) in node. The tiers come from
eng.bp.frames (stubbed here with the Paladin's published Faster Cast table - the card holds no table of its own, which the
source check below pins). RED_PROOF below. [[unknown-stays-unknown]]
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII ('10 frames · tier 6/7'): never crash while REPORTING
    _enable()
except Exception:
    pass
BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
NODE = shutil.which("node")
PAL_FCR = [[0, 15], [9, 14], [18, 13], [30, 12], [48, 11], [75, 10], [125, 9]]


def _cut(src, a, b):
    assert src.count(a) == 1, "cut start %r occurs %d times" % (a[:50], src.count(a))
    i = src.index(a)
    return src[i:src.index(b, i)]


def _code(src):
    src = re.sub(r"/\*.{0,4000}?\*/", "", src, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", r"\1", ln) for ln in src.split("\n"))


@unittest.skipUnless(NODE, "node is required to run the page's card code")
class TheBreakpointCardsReadTheEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with io.open(BIBLE, encoding="utf-8") as fh:
            cls.src = fh.read()
        cards = _cut(cls.src, "  function _cbBpTiers(kind, b, eng){", "  function _cbLeftHtml(b, s, L){")
        say = _cut(cls.src, "  function _ceBpNum(n){", "  function _ceBpNow(value){")
        prog = (
            "function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n"
            "var TABLE = %s;\n"
            "function _cbBpWho(b){ return { cls: 'Paladin' }; }\n"
            "function _cbIasGap(b, r){ return { frames: null }; }\n"
            "function framesAt(p){ var f = null; TABLE.forEach(function(t){ if (p >= t[0]) f = t[1]; }); return f; }\n"
            % json.dumps(PAL_FCR)
            + say + "\n" + cards + "\n" + r"""
var eng = { bp: { frames: function(kind, who, p){ return kind === 'fcr' ? framesAt(p) : null; }, say: _ceBpSay } };
function row(v, g){ return { key: 'fcr', source: 'EXACT', value: { min: v, max: v }, bp: g }; }
var out = {
  at105: _cbBpCard('Fast Cast', 'fcr', row(105, { frames: 10, nextPct: 125, need: 20, atCap: false, now: { min: 105, max: 105 } }), eng, {}),
  at0: _cbBpCard('Fast Cast', 'fcr', row(0, { frames: 15, nextPct: 9, need: 9, atCap: false, now: { min: 0, max: 0 } }), eng, {}),
  top: _cbBpCard('Fast Cast', 'fcr', row(130, { frames: 9, nextPct: null, need: 0, atCap: true, now: { min: 130, max: 130 } }), eng, {}),
  unk: _cbBpCard('Attack Speed', 'ias', { key: 'ias', source: 'UNKNOWN', value: null,
         bp: { frames: null, why: 'No weapon is worn, so the attack frames are not known.' } }, eng, {}),
  tiers: _cbBpTiers('fcr', {}, eng)
};
process.stdout.write(JSON.stringify(out));
""")
        r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("node could not run the card code - UNKNOWN, not passing: " + r.stderr[-800:])
        cls.o = json.loads(r.stdout)
        # his 11-08 13:5x: "105 is the top? depending on the build ... sorceress can reach 200%" - the REAL engine, per class
        real = _cut(cls.src, "  var _CE_BP_FCR = {", "  function _ceBpAttach(res, opts){")
        prog2 = (
            "function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;'); }\n"
            "var WHO = { cls: 'Paladin' };\nfunction _cbBpWho(b){ return WHO; }\n"
            "function _cbIasGap(b, r){ return { frames: null }; }\n"
            + real + "\n" + say + "\n" + cards + "\n" + r"""
var eng = { bp: { frames: _ceBpFrames, say: _ceBpSay } };
function card(cls, v){ WHO = { cls: cls }; var g = _ceBpGap('fcr', WHO, v);
  return { html: _cbBpCard('Faster Cast Rate (FCR)', 'fcr', { key: 'fcr', source: 'EXACT', value: { min: v, max: v }, bp: g }, eng, {}),
           tiers: _cbBpTiers('fcr', {}, eng) }; }
process.stdout.write(JSON.stringify({ sorc105: card('Sorceress', 105), sorc200: card('Sorceress', 200),
  pal105: card('Paladin', 105), pal125: card('Paladin', 125) }));
""")
        r2 = subprocess.run([NODE, "-"], input=prog2, capture_output=True, text=True, timeout=60)
        if r2.returncode != 0:
            raise AssertionError("node could not run the real engine with the cards - UNKNOWN, not passing: " + r2.stderr[-800:])
        cls.real = json.loads(r2.stdout)

    @staticmethod
    def _text(html):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()

    def test_his_example_105_percent(self):
        """* THE POINT - Paladin 105% FCR: '10 frames · tier 6/7' and '10 frames. +20% more reaches the next step.'"""
        h = self.o["at105"]
        self.assertIn('<b class="cb-bpc-v">105%</b>', h)
        self.assertIn('<div class="cb-bpc-sub">10 frames · tier 6/7</div>', h)
        self.assertIn('>10 frames. +20% more reaches the next step.</div>', h)
        self.assertIn('class="cb-bpc-mark" style="left:84.00%"', h, "the marker is not at 105 of the rail's 125")
        self.assertEqual(h.count("cb-bpc-tick cb-bpc-on"), 6, "the reached ticks are not the six tiers at or under 105%")

    def test_his_example_0_percent_and_the_top(self):
        self.assertIn('>15 frames. +9% more reaches the next step.</div>', self.o["at0"])
        self.assertIn("tier 1/7", self.o["at0"])
        self.assertIn('>9 frames. Top breakpoint.</div>', self.o["top"], "the top tier does not say 'Top breakpoint'")
        self.assertIn("tier 7/7", self.o["top"])

    def test_the_tiers_come_from_the_engine(self):
        self.assertEqual(self.o["tiers"], PAL_FCR, "the rail's ticks are not the engine's tiers")
        code = _code(_cut(self.src, "  function _cbBpTiers(kind, b, eng){", "  function _cbBpNum(n){"))
        self.assertIn("eng.bp.frames(kind, who, p)", code, "the card reads a table of its own, not the engine's")

    def test_the_top_is_the_classs_own_top(self):
        """* his 11-08 - the top breakpoint depends on the class: a Sorceress tops out at 200% (7 frames), a Paladin at 125%"""
        R = self.real
        self.assertEqual(R["sorc105"]["tiers"][-1], [200, 7], "the Sorceress rail does not end at her 200%%: %r" % R["sorc105"]["tiers"])
        self.assertEqual(R["pal105"]["tiers"][-1], [125, 9], "the Paladin rail does not end at his 125%%: %r" % R["pal105"]["tiers"])
        self.assertIn(">8 frames. +95% more reaches the next step.", R["sorc105"]["html"], "a Sorceress at 105% is not one step from her top")
        self.assertIn("tier 6/7", R["sorc105"]["html"])
        self.assertIn(">7 frames. Top breakpoint.", R["sorc200"]["html"])
        self.assertIn("tier 7/7", R["sorc200"]["html"])
        self.assertIn(">10 frames. +20% more reaches the next step.", R["pal105"]["html"])
        self.assertIn(">9 frames. Top breakpoint.", R["pal125"]["html"])
        self.assertNotIn("Top breakpoint", R["sorc105"]["html"].split("Lightning")[0], "105% read as the top for a Sorceress")

    def test_unknown_says_why_and_draws_no_rail(self):
        h = self.o["unk"]
        self.assertIn("UNKNOWN. No weapon is worn, so the attack frames are not known.", self._text(h))
        self.assertNotIn("cb-bpc-rail", h, "a card with no answer drew a rail")
        self.assertIn('<b class="cb-bpc-v">—</b>', h)

    def test_the_screen_holds_the_panel_and_not_the_three_he_removed(self):
        code = _code(_cut(self.src, "  function _cbLeftHtml(b, s, L){", "  function _cbRender(){"))
        self.assertIn("Breakpoints", code)
        for gone in ("cb-stashp", "cb-loot", "cb-sw"):
            self.assertNotIn(gone, code, "%s is back on the build screen (his rules 1-3)" % gone)
        self.assertIn("return h + '</div>' + _cbPrimMercHtml() + '</div>';", _code(self.src),
                      "Primary Skills and Mercenary are not under Stats (his rule 4)")


RED_PROOF = [
    {"why": "v3885 (#134) - the top tier says 'This is the last step' again, not his 'Top breakpoint'",
     "file": "bible.html",
     "find": "      if (g.atCap) return _ceBpNum(g.frames) + ' frames. Top breakpoint.';   /* v3885 (#134, his words) */\n",
     "replace": "      if (g.atCap) return _ceBpNum(g.frames) + ' frames. This is the last step.';\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#134) - the tier label counts every tick, reached or not (the gauge and the label disagree)",
     "file": "bible.html",
     "find": "      var now = v.min, k = tiers.filter(function(t){ return t[0] <= now; }).length, T = tiers.length;\n",
     "replace": "      var now = v.min, k = tiers.length, T = tiers.length;\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#134) - the marker sits at the rail's end whatever the value",
     "file": "bible.html",
     "find": "        + '<span class=\"cb-bpc-mark\" style=\"left:' + pos(now) + '\"></span></div>';\n",
     "replace": "        + '<span class=\"cb-bpc-mark\" style=\"left:100%\"></span></div>';\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#134) - a card with no answer still draws a rail",
     "file": "bible.html",
     "find": "    var tiers = (g && g.frames != null && v) ? _cbBpTiers(kind, b, eng) : null, sub = '', rail = '';\n",
     "replace": "    var tiers = _cbBpTiers('fcr', b, eng), sub = '', rail = '';\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#134, his 11-08) - the rail stops at 150%, so a Sorceress's 200% top is never drawn and 105% reads one step short of a top it cannot see",
     "file": "bible.html",
     "find": "      var who = _cbBpWho(b), out = [], last = null, cap = kind === 'fcr' ? 300 : 600;\n",
     "replace": "      var who = _cbBpWho(b), out = [], last = null, cap = kind === 'fcr' ? 150 : 600;\n", "matches": 1, "needs": "node"},
    {"why": "v3885 (#134) - the Stash card is back on the build screen",
     "file": "bible.html",
     "find": "    return '<div class=\"cb-left\"><div class=\"cb-p cb-bpp\">",
     "replace": "    return '<div class=\"cb-left\"><div class=\"cb-p cb-stashp\"></div><div class=\"cb-p cb-bpp\">", "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
