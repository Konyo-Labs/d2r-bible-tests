# -*- coding: utf-8 -*-
"""v3888 (REG-3487, the sweep of REG-3485) - A BEST RUN THAT IS NOT A BOSS OPENS NO BOSS CARD, AND WEARS ITS OWN PICTURE.

#155 (v3887) made a super-unique a Best run - Normal Coldcrow is silospen's All #1 for Bane Ash - and two surfaces only knew
bosses. GitHub's round on v3887 caught the run row (v1624: "Normal Coldcrow has no boss anchor" - it wore the "no verified
farm source yet" question mark, REG-3485). The sweep found the hero above the rows: _bossHeroName drew any run as a button
"open the Normal Coldcrow boss card" whose click asked openBossDetail for an id BOSSES does not have - a control that looks
pressable and does nothing, with no picture.

Now both: a boss keeps its portrait and its card; a super-unique wears its own sprite (_QW_SU_ART, the map Quick wins draws
from) and floats its monster's card by name, with no boss card; any other id that is not a boss is its plain name - never a
dead button, never a question mark that says "we do not know where this drops" about a verified run.

Both functions are cut from bible.html between their own boundaries and driven in node. RED_PROOF below.
[[the-unjoined-end]] [[unknown-stays-unknown]]
"""
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable as _enable   # it prints non-ASCII: never crash while REPORTING
    _enable()
except Exception:
    pass
NODE = shutil.which("node") or shutil.which("nodejs")


def _src():
    with io.open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as fh:
        return fh.read()


def _cut(src, start, end):
    assert src.count(start) == 1, "cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start))
    i = src.index(start)
    return src[i:src.index(end, i + len(start)) + len(end)]


_DRIVER = r"""
var BOSSES = [{id: 'mephisto', name: 'Mephisto'}];
var _QW_SU_ART = {su_coldcrow: 'd2mon_Coldcrow.gif'};
var window = {};
function esc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }
function jsq(s){ return String(s).replace(/'/g, "\\'"); }
function _artV(u){ return u + '?v=test'; }
function _runBossArt(id){ return id === 'mephisto' ? {url: 'art/d2mon_Mephisto.gif?v=test', name: 'Mephisto', emoji: ''} : null; }
%s
%s
var items = [{_bs: {s: {name: 'Coldcrow'}}}];
process.stdout.write(JSON.stringify({
  heroBoss: _bossHeroName({boss: 'Hell Mephisto', bossId: 'mephisto'}),
  heroSu: _bossHeroName({boss: 'Normal Coldcrow', bossId: 'su_coldcrow', items: items}),
  heroOther: _bossHeroName({boss: 'Somewhere', bossId: 'nobody_here'}),
  thumbBoss: _runArtThumb({boss: 'Hell Mephisto', bossId: 'mephisto'}),
  thumbSu: _runArtThumb({boss: 'Normal Coldcrow', bossId: 'su_coldcrow', items: items}),
  thumbNone: _runArtThumb({boss: 'Anywhere', bossId: null})
}));
"""


@unittest.skipUnless(NODE, "node is required to run the page's functions - UNMEASURED without it")
class ARunThatIsNotABossOpensNoBossCard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        src = _src()
        hero = _cut(src, "  function _bossHeroName(r){", "\n  }\n")
        thumb = _cut(src, "  function _runArtThumb(r){", "\n  }\n")
        r = subprocess.run([NODE, "-"], input=_DRIVER % (hero, thumb), capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError("driver failed: " + (r.stderr or r.stdout)[-1500:])
        cls.o = json.loads(r.stdout)

    def test_premise_a_boss_keeps_its_portrait_and_its_card(self):
        for k in ("heroBoss", "thumbBoss"):
            self.assertIn("openBossDetail('mephisto')", self.o[k], "%s lost the boss card: %s" % (k, self.o[k]))
            self.assertIn("d2mon_Mephisto.gif", self.o[k])

    def test_a_super_unique_hero_wears_its_sprite_and_opens_no_boss_card(self):
        """* THE POINT - the hero above the rows: no dead button, its own sprite, its monster's card by name"""
        h = self.o["heroSu"]
        self.assertNotIn("openBossDetail", h, "the hero opens a boss card a super-unique does not have: %s" % h)
        self.assertNotIn('role="button"', h, "the hero still looks pressable: %s" % h)
        self.assertNotIn("boss card", h, "the hero still promises a boss card: %s" % h)
        self.assertIn('src="art/d2mon_Coldcrow.gif?v=test"', h, "the hero does not wear the super-unique's sprite")
        self.assertIn('data-arttip="Coldcrow"', h, "the hero floats no card for the monster")
        self.assertIn("Normal Coldcrow", h)

    def test_a_super_unique_run_row_wears_its_sprite_not_a_question_mark(self):
        t = self.o["thumbSu"]
        self.assertNotIn("no verified farm source yet", t, "a verified super-unique run reads 'no verified source': %s" % t)
        self.assertNotIn("openBossDetail", t)
        self.assertIn('data-su-tip="su_coldcrow"', t)
        self.assertIn('src="art/d2mon_Coldcrow.gif?v=test"', t)

    def test_an_id_that_is_no_boss_and_no_super_unique_is_a_plain_name(self):
        h = self.o["heroOther"]
        self.assertNotIn("openBossDetail", h, "a dead boss-card button for an unknown id: %s" % h)
        self.assertIn("Somewhere", h)
        self.assertIn("no verified farm source yet", self.o["thumbNone"], "BASELINE: a run with no source lost its honest glyph")


RED_PROOF = [
    {"why": "v3888 (REG-3487) - the hero draws a super-unique run as a dead 'open the boss card' button again",
     "file": "bible.html",
     "find": "    if (!_hB.some(function(B){ return B && B.id === r.bossId; })) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
    {"why": "v3888 (REG-3487) - a super-unique hero loses its sprite",
     "file": "bible.html",
     "find": "      var _hSu = (typeof _QW_SU_ART !== 'undefined' && _QW_SU_ART) ? _QW_SU_ART[r.bossId] : null;\n",
     "replace": "      var _hSu = null;\n",
     "matches": 1, "needs": "node"},
    {"why": "v3887 (REG-3485) - a super-unique run row wears 'no verified farm source yet' again",
     "file": "bible.html",
     "find": "    if (!b && r.bossId && typeof _QW_SU_ART !== 'undefined' && _QW_SU_ART[r.bossId]) {\n",
     "replace": "    if (false) {\n",
     "matches": 1, "needs": "node"},
]


if __name__ == "__main__":
    unittest.main()
