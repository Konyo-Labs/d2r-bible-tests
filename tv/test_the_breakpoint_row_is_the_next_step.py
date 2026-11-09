# -*- coding: utf-8 -*-
"""#153 — THE NEXT STEP IS THE SHEET'S OWN TOTAL, FOR THE CLASS THAT IS WEARING IT.

The Stats column already sums worn gear and inventory charms into one percent. This row says what
that percent is in frames, and how much more of the same stat reaches the next step. The class
table is not drawn. A range that straddles a step says both frame counts.

TWO WITNESSES. The page computes frames from the published formula. This file holds the published
frame tables, copied from the maxroll Patch 2.4 breakpoints page (fetched 2026-10-04), and walks
every integer percent from 0 through the last listed cell. The four printed casting bases that do
not reproduce those tables stay asserted as disagreements: Druid human, Werewolf and Werebear are
printed 16 and the Necromancer is printed 15. A planted wrong base goes red.

The builder paints that gap under the existing speed rows. An inventory charm moves the same
total: Annihilus changes fire resistance and leaves the Faster Cast Rate step where it was, and
of Balance on a small charm moves Faster Hit Recovery. A Shimmering Small Charm of Balance
on a level 1 Paladin stays out of those rows until the build reaches its required level, and a
worn magic item follows the same line. Increased Attack Speed uses the page's own
_cbFpa, not a second formula. Warlock frames stay unpublished, with the 125% Faster Cast Rate
target. Holy Shield is not on this build.

RED_PROOF below.
"""
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
    from console_safe import enable as _enable
    _enable()
except Exception:
    pass

import test_the_character_builder_is_joined_to_the_engine_and_the_mule_window as JOIN  # noqa: E402

NODE = shutil.which("node")
OPEN = '<script id="v174-char-engine-js">'

# [percent, frames] — the first percent that reaches that frame count. Action-flag-only rows are not frames.
# The walk stops at the last cell this transcription could read on the page. A later formula step is not
# listed here. The Barbarian block table stops at 3 frames; 2 frames at 280% is the formula's next step.
TABLES = [
    ("fcr", {"cls": "Amazon", "weapon": "other"},
     [[0, 19], [7, 18], [14, 17], [22, 16], [32, 15], [48, 14], [68, 13], [99, 12], [152, 11]]),
    ("fcr", {"cls": "Assassin", "weapon": "other"},
     [[0, 16], [8, 15], [16, 14], [27, 13], [42, 12], [65, 11], [102, 10], [174, 9]]),
    ("fcr", {"cls": "Barbarian", "weapon": "other"},
     [[0, 13], [9, 12], [20, 11], [37, 10], [63, 9], [105, 8], [200, 7]]),
    ("fcr", {"cls": "Druid", "weapon": "other"},
     [[0, 18], [4, 17], [10, 16], [19, 15], [30, 14], [46, 13], [68, 12], [99, 11], [163, 10]]),
    ("fcr", {"cls": "Druid", "form": "wolf", "weapon": "other"},
     [[0, 16], [6, 15], [14, 14], [26, 13], [40, 12], [60, 11], [95, 10], [157, 9]]),
    ("fcr", {"cls": "Druid", "form": "bear", "weapon": "other"},
     [[0, 16], [7, 15], [15, 14], [26, 13], [40, 12], [63, 11], [99, 10], [163, 9]]),
    ("fcr", {"cls": "Necromancer", "weapon": "other"},
     [[0, 15], [9, 14], [18, 13], [30, 12], [48, 11], [75, 10], [125, 9]]),
    ("fcr", {"cls": "Necromancer", "form": "vampire", "weapon": "other"},
     [[0, 23], [6, 22], [11, 21], [18, 20], [24, 19], [35, 18], [48, 17], [65, 16], [86, 15], [120, 14], [180, 13]]),
    ("fcr", {"cls": "Paladin", "weapon": "other"},
     [[0, 15], [9, 14], [18, 13], [30, 12], [48, 11], [75, 10], [125, 9]]),
    ("fcr", {"cls": "Sorceress", "weapon": "other"},
     [[0, 13], [9, 12], [20, 11], [37, 10], [63, 9], [105, 8], [200, 7]]),
    ("fhr", {"cls": "Amazon", "weapon": "other"},
     [[0, 11], [6, 10], [13, 9], [20, 8], [32, 7], [52, 6], [86, 5], [174, 4]]),
    ("fhr", {"cls": "Assassin", "weapon": "other"},
     [[0, 9], [7, 8], [15, 7], [27, 6], [48, 5], [86, 4], [200, 3]]),
    ("fhr", {"cls": "Barbarian", "weapon": "other"},
     [[0, 9], [7, 8], [15, 7], [27, 6], [48, 5], [86, 4], [200, 3]]),
    ("fhr", {"cls": "Druid", "weapon": "1h-swing"},
     [[0, 14], [3, 13], [7, 12], [13, 11], [19, 10], [29, 9], [42, 8], [63, 7], [99, 6], [174, 5], [456, 4]]),
    ("fhr", {"cls": "Druid", "weapon": "other"},
     [[0, 13], [5, 12], [10, 11], [16, 10], [26, 9], [39, 8], [56, 7], [86, 6], [152, 5], [377, 4]]),
    ("fhr", {"cls": "Druid", "form": "wolf", "weapon": "other"},
     [[0, 7], [9, 6], [20, 5], [42, 4], [86, 3], [280, 2]]),
    ("fhr", {"cls": "Druid", "form": "bear", "weapon": "other"},
     [[0, 13], [5, 12], [10, 11], [16, 10], [24, 9], [37, 8], [54, 7], [86, 6], [152, 5], [360, 4]]),
    ("fhr", {"cls": "Necromancer", "weapon": "other"},
     [[0, 13], [5, 12], [10, 11], [16, 10], [26, 9], [39, 8], [56, 7], [86, 6], [152, 5], [377, 4]]),
    ("fhr", {"cls": "Necromancer", "form": "vampire", "weapon": "other"},
     [[0, 15], [2, 14], [6, 13], [10, 12], [16, 11], [24, 10], [34, 9], [48, 8], [72, 7], [117, 6], [208, 5]]),
    ("fhr", {"cls": "Paladin", "weapon": "spear"},
     [[0, 13], [3, 12], [7, 11], [13, 10], [20, 9], [32, 8], [48, 7], [75, 6], [129, 5], [280, 4]]),
    ("fhr", {"cls": "Paladin", "weapon": "other"},
     [[0, 9], [7, 8], [15, 7], [27, 6], [48, 5], [86, 4], [200, 3]]),
    ("fhr", {"cls": "Sorceress", "weapon": "other"},
     [[0, 15], [5, 14], [9, 13], [14, 12], [20, 11], [30, 10], [42, 9], [60, 8], [86, 7], [142, 6], [280, 5]]),
    ("fbr", {"cls": "Amazon", "weapon": "1h-swing"},
     [[0, 17], [4, 16], [6, 15], [11, 14], [15, 13], [23, 12], [29, 11], [40, 10], [56, 9], [80, 8], [120, 7]]),
    ("fbr", {"cls": "Amazon", "weapon": "other"},
     [[0, 5], [13, 4], [32, 3], [86, 2]]),
    ("fbr", {"cls": "Assassin", "weapon": "other"},
     [[0, 5], [13, 4], [32, 3], [86, 2]]),
    ("fbr", {"cls": "Barbarian", "weapon": "other"},
     [[0, 7], [9, 6], [20, 5], [42, 4], [86, 3]]),
    ("fbr", {"cls": "Druid", "weapon": "other"},
     [[0, 11], [6, 10], [13, 9], [20, 8], [32, 7], [52, 6], [86, 5]]),
    ("fbr", {"cls": "Druid", "form": "wolf", "weapon": "other"},
     [[0, 9], [7, 8], [15, 7], [27, 6], [48, 5], [86, 4]]),
    ("fbr", {"cls": "Druid", "form": "bear", "weapon": "other"},
     [[0, 12], [5, 11], [10, 10], [16, 9], [27, 8], [40, 7], [65, 6], [109, 5]]),
    ("fbr", {"cls": "Necromancer", "weapon": "other"},
     [[0, 11], [6, 10], [13, 9], [20, 8], [32, 7], [52, 6], [86, 5]]),
    ("fbr", {"cls": "Paladin", "weapon": "other", "holyShield": False},
     [[0, 5], [13, 4], [32, 3], [86, 2]]),
    ("fbr", {"cls": "Paladin", "weapon": "other", "holyShield": True},
     [[0, 2], [86, 1]]),
    ("fbr", {"cls": "Sorceress", "weapon": "other"},
     [[0, 9], [7, 8], [15, 7], [27, 6], [48, 5], [86, 4], [200, 3]]),
]

LIGHTNING = [[0, 19], [7, 18], [15, 17], [23, 16], [35, 15], [52, 14], [78, 13], [117, 12], [194, 11]]


def _src():
    with open(os.path.join(ROOT, "bible.html"), encoding="utf-8") as f:
        return f.read()


def _engine(src):
    assert src.count(OPEN) == 1, "the engine script is not there exactly once"
    i = src.index(OPEN) + len(OPEN)
    return src[i:src.index("</script>", i)]


DRIVER = r"""
var window = {};
%(engine)s
var E = window.D2R_CHAR_ENGINE, TABLES = %(tables)s, LIGHT = %(light)s, bad = [];
function expect(steps, p){
  var f = steps[0][1];
  for (var i = 0; i < steps.length; i++) if (steps[i][0] <= p) f = steps[i][1];
  return f;
}
TABLES.forEach(function(t){
  var steps = t[2], last = steps[steps.length - 1][0];
  for (var p = 0; p <= last && bad.length < 8; p++){
    var got = E.bp.frames(t[0], t[1], p), want = expect(steps, p);
    if (got !== want) bad.push(t[0] + ' ' + JSON.stringify(t[1]) + ' @' + p + ' got ' + got + ' want ' + want);
  }
  steps.forEach(function(s){
    if (!s[0] || bad.length >= 8) return;
    var prev = E.bp.frames(t[0], t[1], s[0] - 1);
    if (!(prev > s[1])) bad.push('not a step ' + t[0] + ' ' + s[0] + ' prev ' + prev);
  });
});
for (var p = 0; p <= 194 && bad.length < 12; p++){
  var gotL = E.bp.frames('fcr', { cls: 'Sorceress', lightning: true, weapon: 'other' }, p);
  if (gotL !== expect(LIGHT, p)) bad.push('lightning @' + p + ' got ' + gotL + ' want ' + expect(LIGHT, p));
}
function say(kind, who, value){ var g = E.bp.gap(kind, who, value); return { say: E.bp.say(g), gap: g }; }
function sheet(build, opts){ return E.sheet(build, opts); }
function row(sh, key){ return sh.rows.filter(function(r){ return r.key === key; })[0]; }
var who = { cls: 'Sorceress', weapon: 'other', holyShield: false };
var gear = { cls: 'Sorceress', level: 90, sets: [{ slots: {
  tors: { name: 'Skin of the Vipermagi' }, rarm: { name: 'The Oculus' } } }] };
var withCharm = JSON.parse(JSON.stringify(gear));
withCharm.sets[0].inv = [{ name: 'Annihilus', rolls: { 'res-all': 20 } }];
var opt = { difficulty: 'Hell', quests: true, bp: who };
var bare = sheet(gear, opt), held = sheet(withCharm, opt);
var noBp = sheet(gear, { difficulty: 'Hell', quests: true });
var charmBuild = { cls: 'Sorceress', level: 88, sets: [{ slots: {
  head: { name: 'Crown of Ages' }, tors: { name: 'Skin of the Vipermagi' },
  neck: { name: "Mara's Kaleidoscope" }, rarm: { name: 'The Oculus' } },
  inv: [{ name: 'Small Charm', quality: 'magic', base: 'cm1' }] }] };
var crownBuild = JSON.parse(JSON.stringify(charmBuild));
crownBuild.sets[0].inv = [];
var charm = sheet(charmBuild, { difficulty: 'Hell', quests: true, bp: who });
var crown = sheet(crownBuild, { difficulty: 'Hell', quests: true, bp: who });
process.stdout.write(JSON.stringify({
  bad: bad,
  api: Object.keys(E).sort(),
  printed: {
    dru0: E.bp.framesWith('fcr', 16, 208, 0, {}),
    wolf0: E.bp.framesWith('fcr', 16, 229, 0, {}),
    bear0: E.bp.framesWith('fcr', 16, 228, 0, {}),
    nec86: E.bp.framesWith('fcr', 15, 256, 86, {}),
    planted: E.bp.framesWith('fcr', 13, 256, 0, {})
  },
  work: {
    dru0: E.bp.frames('fcr', { cls: 'Druid', weapon: 'other' }, 0),
    wolf0: E.bp.frames('fcr', { cls: 'Druid', form: 'wolf', weapon: 'other' }, 0),
    bear0: E.bp.frames('fcr', { cls: 'Druid', form: 'bear', weapon: 'other' }, 0),
    nec86: E.bp.frames('fcr', { cls: 'Necromancer', weapon: 'other' }, 86),
    nec125: E.bp.frames('fcr', { cls: 'Necromancer', weapon: 'other' }, 125),
    sor0: E.bp.frames('fcr', who, 0)
  },
  say60: say('fcr', who, { min: 60, max: 60 }),
  say30: say('fcr', who, { min: 30, max: 30 }),
  straddle: say('fcr', who, { min: 60, max: 70 }),
  inside: say('fcr', who, { min: 50, max: 60 }),
  amaLast: say('fcr', { cls: 'Amazon', weapon: 'other' }, 152),
  sorLast: say('fcr', who, 200),
  war0: say('fcr', { cls: 'Warlock', weapon: 'other' }, 0),
  war130: say('fcr', { cls: 'Warlock', weapon: 'other' }, { min: 130, max: 140 }),
  warRange: say('fcr', { cls: 'Warlock', weapon: 'other' }, { min: 100, max: 140 }),
  warFhr: say('fhr', { cls: 'Warlock', weapon: 'other' }, 0),
  druUnknown: say('fhr', { cls: 'Druid' }, 0),
  palUnknown: say('fhr', { cls: 'Paladin' }, 0),
  amaUnknown: say('fbr', { cls: 'Amazon' }, 0),
  amaOther: say('fbr', { cls: 'Amazon', weapon: 'other' }, 0),
  amaSwing: say('fbr', { cls: 'Amazon', weapon: '1h-swing' }, 0),
  druOther: say('fhr', { cls: 'Druid', weapon: 'other' }, 0),
  druSwing: say('fhr', { cls: 'Druid', weapon: '1h-swing' }, 0),
  palSpear: say('fhr', { cls: 'Paladin', weapon: 'spear' }, 0),
  palOther: say('fhr', { cls: 'Paladin', weapon: 'other' }, 0),
  hsOff: say('fbr', { cls: 'Paladin', weapon: 'other', holyShield: false }, 0),
  hsOn: say('fbr', { cls: 'Paladin', weapon: 'other', holyShield: true }, 50),
  barbNext: say('fbr', { cls: 'Barbarian', weapon: 'other' }, 86),
  amaFcrUnknownWeapon: E.bp.frames('fcr', { cls: 'Amazon' }, 0),
  noClsFcr: say('fcr', { weapon: 'other' }, 0),
  noClsFhr: say('fhr', { cls: '' }, 0),
  noClsFbr: say('fbr', {}, 0),
  oddClsFcr: say('fcr', { cls: 'Monk', weapon: 'other' }, 0),
  palFcr0: say('fcr', { cls: 'Paladin', weapon: 'other' }, 0),
  bareFire: row(bare, 'res-fire').value,
  heldFire: row(held, 'res-fire').value,
  bareFcr: row(bare, 'fcr').bp,
  heldFcr: row(held, 'fcr').bp,
  noBp: Object.prototype.hasOwnProperty.call(row(noBp, 'fcr'), 'bp'),
  charmFcr: row(charm, 'fcr').value,
  charmFhr: { source: row(charm, 'fhr').source, frames: row(charm, 'fhr').bp && row(charm, 'fhr').bp.frames },
  crownFhr: { source: row(crown, 'fhr').source, value: row(crown, 'fhr').value,
    frames: row(crown, 'fhr').bp && row(crown, 'fhr').bp.frames,
    need: row(crown, 'fhr').bp && row(crown, 'fhr').bp.need },
  charmFire: row(charm, 'res-fire').source
}));
"""


def _engine_out():
    src = _src()
    js = DRIVER % {"engine": _engine(src), "tables": json.dumps(TABLES), "light": json.dumps(LIGHTNING)}
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        raise AssertionError("the breakpoint engine would not run: %s" % (r.stderr or "")[-1500:])
    return json.loads(r.stdout)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheFormulaMatchesThePublishedTables(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.out = _engine_out()

    def test_every_listed_percent_matches_and_a_wrong_base_does_not(self):
        self.assertEqual(self.out["bad"], [], "the formula left the published table: %s" % self.out["bad"][:8])
        self.assertEqual(self.out["work"]["dru0"], 18)
        self.assertNotEqual(self.out["printed"]["dru0"], 18, "the printed Druid base of 16 was treated as the table")
        self.assertEqual(self.out["work"]["wolf0"], 16)
        self.assertNotEqual(self.out["printed"]["wolf0"], 16)
        self.assertEqual(self.out["work"]["bear0"], 16)
        self.assertNotEqual(self.out["printed"]["bear0"], 16)
        self.assertEqual(self.out["work"]["nec86"], 10)
        self.assertEqual(self.out["work"]["nec125"], 9)
        self.assertEqual(self.out["printed"]["nec86"], 9, "the printed Necromancer base would call 86% a 9-frame step")
        self.assertEqual(self.out["work"]["sor0"], 13)
        self.assertNotEqual(self.out["printed"]["planted"], 13, "a planted casting base of 13 still reproduced the table")
        self.assertEqual(self.out["amaFcrUnknownWeapon"], 19, "Amazon cast frames do not depend on the weapon")

    def test_the_sentence_is_the_next_step_and_a_range_says_both(self):
        self.assertEqual(self.out["say60"]["say"],
                         "10 frames. +3% more reaches the next step. Lightning and Chain Lightning: 14 frames. +18% more reaches the next step.")
        self.assertEqual(self.out["say60"]["gap"]["nextPct"], 63)
        self.assertEqual(self.out["say60"]["gap"]["need"], 3)
        self.assertEqual(self.out["say60"]["gap"]["stat"], "fcr")
        self.assertEqual(self.out["say30"]["say"].split(" Lightning")[0], "11 frames. +7% more reaches the next step.")
        self.assertEqual(self.out["straddle"]["say"].split(" Lightning")[0],
                         "10 or 9 frames. The low end needs +3% more. The high end needs +35% more.")
        self.assertEqual(self.out["inside"]["say"].split(" Lightning")[0],
                         "10 frames. The low end needs +13% more. The high end needs +3% more.")
        self.assertEqual(self.out["amaLast"]["say"], "11 frames. Top breakpoint.")
        self.assertTrue(self.out["amaLast"]["gap"]["atCap"])
        self.assertEqual(self.out["sorLast"]["say"].split(" Lightning")[0], "7 frames. Top breakpoint.")

    def test_unknown_stays_unknown_and_holy_shield_is_not_assumed(self):
        self.assertIn("125%", self.out["war0"]["say"])
        self.assertNotRegex(self.out["war0"]["say"], r"\d+ frames")
        self.assertIsNone(self.out["war0"]["gap"]["frames"])
        self.assertEqual(self.out["war0"]["gap"]["nextPct"], 125)
        self.assertEqual(self.out["war0"]["gap"]["need"], 125)
        self.assertIn("already reached", self.out["war130"]["say"])
        self.assertIn("The low end needs +25% more", self.out["warRange"]["say"])
        self.assertIn("The high end has reached 125%", self.out["warRange"]["say"])
        self.assertNotRegex(self.out["warFhr"]["say"], r"\d+ frames")
        self.assertIn("1-hand swinging", self.out["druUnknown"]["say"])
        self.assertIn("spear or a staff", self.out["palUnknown"]["say"])
        self.assertIn("1-hand swinging", self.out["amaUnknown"]["say"])
        self.assertEqual(self.out["amaOther"]["gap"]["frames"], 5)
        self.assertEqual(self.out["amaSwing"]["gap"]["frames"], 17)
        self.assertEqual(self.out["druOther"]["gap"]["frames"], 13)
        self.assertEqual(self.out["druSwing"]["gap"]["frames"], 14)
        self.assertEqual(self.out["palSpear"]["gap"]["frames"], 13)
        self.assertEqual(self.out["palOther"]["gap"]["frames"], 9)
        self.assertIn("Holy Shield is not on this build", self.out["hsOff"]["gap"]["why"])
        self.assertNotIn("Holy Shield", self.out["hsOff"]["say"])
        self.assertEqual(self.out["hsOff"]["gap"]["frames"], 5)
        self.assertEqual(self.out["hsOn"]["gap"]["frames"], 2)
        self.assertEqual(self.out["barbNext"]["gap"]["frames"], 3)
        self.assertEqual(self.out["barbNext"]["gap"]["nextPct"], 280)
        self.assertNotIn(280, [s[0] for s in TABLES[25][2]])

    def test_a_build_with_no_class_says_no_class_is_chosen(self):
        """v3889 (GrokBot 6734314659): the + New character dialog's unsaved draft has no class, and its cards said "This
        class has no published FCR table" - a false reason. No class is its own UNKNOWN; a class the tables do not know
        keeps the table sentence; a Paladin reads its frames."""
        for k in ("noClsFcr", "noClsFhr", "noClsFbr"):
            self.assertIsNone(self.out[k]["gap"]["frames"], "%s quoted frames for a build with no class" % k)
            self.assertIn("No class is chosen yet", self.out[k]["say"], "%s: %s" % (k, self.out[k]["say"]))
            self.assertNotIn("This class has no published", self.out[k]["say"])
        self.assertIn("This class has no published FCR table", self.out["oddClsFcr"]["say"],
                      "BASELINE: a class the tables do not hold no longer says so")
        self.assertEqual(self.out["palFcr0"]["gap"]["frames"], 15, "BASELINE: a Paladin at 0% is 15 cast frames")

    def test_the_charm_and_the_gear_are_one_total_and_a_blank_call_guesses_nothing(self):
        self.assertEqual(self.out["bareFcr"]["need"], 3)
        self.assertEqual(self.out["heldFcr"]["need"], 3, "Annihilus changed the Faster Cast Rate step")
        self.assertEqual(self.out["bareFcr"]["frames"], 10)
        self.assertGreater(self.out["heldFire"]["max"], self.out["bareFire"]["max"],
                           "Annihilus in the inventory did not join the same sheet: %s -> %s" % (self.out["bareFire"], self.out["heldFire"]))
        self.assertFalse(self.out["noBp"], "a sheet call without a breakpoint request grew a guessed weapon gap")
        self.assertEqual(self.out["charmFcr"], {"min": 60, "max": 60})
        self.assertEqual(self.out["charmFire"], "UNKNOWN")
        self.assertEqual(self.out["charmFhr"]["source"], "UNKNOWN")
        self.assertIsNone(self.out["charmFhr"]["frames"],
                          "an untyped charm hid its Faster Hit Recovery and the step still quoted a frame count")
        self.assertEqual(self.out["crownFhr"]["source"], "EXACT")
        self.assertEqual(self.out["crownFhr"]["value"], {"min": 30, "max": 30})
        self.assertEqual(self.out["crownFhr"]["frames"], 10,
                         "Crown of Ages is 30% Faster Hit Recovery, 10 frames on this Sorceress, not the 0% count of 15")
        self.assertEqual(self.out["crownFhr"]["need"], 12)


@unittest.skipIf(NODE is None, "node is absent - this law is UNMEASURED, not passing")
class TheBuilderPaintsTheSameStep(unittest.TestCase):

    def test_equipment_and_inventory_move_one_row(self):
        out = JOIN._run(r"""
          function bpOf(label){
            var h = statsHtml(), i = h.indexOf('<span class="cb-sl">' + label + '</span>');
            if (i < 0) return null;
            var row = h.slice(i, h.indexOf('</div>', i)), j = row.indexOf('class="cb-bp"');
            if (j < 0) return '';
            return row.slice(row.indexOf('>', j) + 1, row.indexOf('</span>', j));
          }
          function valOf(key){
            var eb = window._cbEngineBuild(cur()), st = window._cbState();
            var sh = window.D2R_CHAR_ENGINE.sheet(eb.build, { difficulty: st.diff, quests: !!st.quests });
            var r = sh.rows.filter(function(x){ return x.key === key; })[0];
            return r ? { value: r.value, source: r.source } : null;
          }
          mk('Sorceress', 90);
          OUT.iasBare = bpOf('Increased Attack Speed');
          OUT.fcrBare = bpOf('Faster Cast Rate');
          wear([['tors', 'Skin of the Vipermagi'], ['rarm', 'The Oculus']]);
          OUT.fcr = bpOf('Faster Cast Rate');
          OUT.fhr = bpOf('Faster Hit Recovery');
          OUT.fire = row(statsHtml(), 'Fire Resistance');
          window._cbOpenPick('inv', null, [1, 0]); window._cbChoose(byName('Annihilus')[0]); window._cbClosePick();
          OUT.fcrAnni = bpOf('Faster Cast Rate');
          OUT.fireAnni = row(statsHtml(), 'Fire Resistance');
          OUT.anniFcr = valOf('fcr');
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm1');
          OUT.tab = window._cbState().pick && window._cbState().pick.tab;
          OUT.fhrUntyped = bpOf('Faster Hit Recovery');
          OUT.fhrUntypedRow = valOf('fhr');
          OUT.fcrUntyped = bpOf('Faster Cast Rate');
          OUT.added = window._cbAddMod('s267');
          OUT.modSay = window._cbState().modSay || '';
          window._cbClosePick();
          OUT.fhrCharm = bpOf('Faster Hit Recovery');
          OUT.fhrCharmRow = valOf('fhr');
          OUT.fcrCharm = bpOf('Faster Cast Rate');
          window._cbView('calc');
          OUT.calc = ELS['cb-win']._html;
          mk('Warlock', 90);
          OUT.war = bpOf('Faster Cast Rate');
          mk('Amazon', 90);
          OUT.amaBare = bpOf('Faster Block Rate');
          OUT.amaFbr = valOf('fbr');
          wear([['rarm', 'Lightsabre']]);
          OUT.amaSword = bpOf('Faster Block Rate');
          OUT.amaSwordFbr = valOf('fbr');
          OUT.amaIas = bpOf('Increased Attack Speed');
          var d = window._cbDb(), e = cur().sets[0].slots.rarm, b = d.b[e.base];
          var c = d.cls[d.clsByName.amazon], wc = String((b[14] === 2 || b[14] === 12) ? b[27] : b[26]).toUpperCase();
          var an = d.tip.an[c.tok][wc], ias = valOf('ias').value.min;
          OUT.fpa = window._cbFpa(an[0], an[1], ias, b[24] | 0);
          OUT.fpaWrong = Math.ceil(256 * an[0] / Math.max(1, Math.floor(an[1] * (100 + ias - (b[24] | 0)) / 100)));
          OUT.hands = b[14]; OUT.type = b[1]; OUT.anc = Object.keys(d.anc[b[1]] || {});
          mk('Druid', 90);
          OUT.druBare = bpOf('Faster Hit Recovery');
          OUT.druFhr = valOf('fhr');
          wear([['rarm', 'Lightsabre']]);
          OUT.druSword = bpOf('Faster Hit Recovery');
          OUT.druSwordFhr = valOf('fhr');
          mk('Assassin', 90);
          wear([['larm', 'Lightsabre']]);
          var shael = null;
          window._cbDb().sk.forEach(function(s){ if (s[1] === 'Shael Rune') shael = s[0]; });
          var off = cur().sets[0].slots.larm;
          off.sockets = 1; off.socketed = shael ? [shael] : [];
          OUT.shael = shael;
          OUT.offLines = tipOf('larm').lines.join('\n');
          var two = null;
          window._cbDb().it.forEach(function(it){
            if (two || it[2] !== 'u') return;
            var b = window._cbDb().b[it[3]];
            if (b && b[21] === 'w' && b[14] === 12) two = it[1];
          });
          OUT.twoName = two;
          if (two){
            mk('Barbarian', 90); wear([['rarm', two]]);
            OUT.barbIas = bpOf('Increased Attack Speed');
            mk('Amazon', 90); wear([['rarm', two]]);
            OUT.amaTwo = bpOf('Faster Block Rate');
          }
          OUT.owed = /still owed|not built yet/.test(ELS['cb-win']._html);
        """)
        self.assertIn("UNKNOWN", out["iasBare"] or "")
        self.assertNotRegex(out["iasBare"] or "", r"\d+ frames")
        self.assertIn("13 frames. +9% more reaches the next step.", out["fcrBare"] or "")
        self.assertIn("Lightning and Chain Lightning: 19 frames. +7% more reaches the next step.", out["fcrBare"] or "")
        self.assertEqual(out["fcr"],
                         "10 frames. +3% more reaches the next step. Lightning and Chain Lightning: 14 frames. +18% more reaches the next step.")
        self.assertEqual(out["fcrAnni"], out["fcr"], "the inventory charm moved Faster Cast Rate")
        self.assertNotEqual(out["fire"], out["fireAnni"], "Annihilus did not change the fire row beside that step: %s" % out["fireAnni"])
        self.assertEqual(out["anniFcr"]["value"], {"min": 60, "max": 60})
        self.assertEqual(out["fcrUntyped"], out["fcr"], "an untyped small charm blanked Faster Cast Rate")
        self.assertIn("15 frames. +5% more reaches the next step.", out["fhr"] or "")
        if out["fhrUntypedRow"]["source"] == "UNKNOWN":
            self.assertIn("UNKNOWN", out["fhrUntyped"] or "")
            self.assertNotRegex(out["fhrUntyped"] or "", r"\d+ frames")
        self.assertTrue(out["added"], "of Balance was not added: %s" % out["modSay"])
        self.assertEqual(out["fhrCharmRow"]["value"], {"min": 5, "max": 5}, out["fhrCharmRow"])
        self.assertEqual(out["fhrCharm"], "14 frames. +4% more reaches the next step.")
        self.assertEqual(out["fcrCharm"], out["fcr"])
        self.assertIn("14 frames. +4% more reaches the next step.", out["calc"])
        self.assertIn("Run and walk has no frame step.", out["calc"])
        self.assertNotIn("still owed", out["calc"])
        self.assertNotIn("not built yet", out["calc"])
        self.assertIn("125%", out["war"] or "")
        self.assertNotRegex(out["war"] or "", r"\d+ frames")
        self.assertEqual(out["amaFbr"]["value"], {"min": 0, "max": 0})
        self.assertIn("5 frames.", out["amaBare"] or "")
        self.assertEqual(out["amaSwordFbr"]["value"], {"min": 0, "max": 0}, out["amaSwordFbr"])
        self.assertIn("17 frames.", out["amaSword"] or "", "Lightsabre was not read as a 1-hand swinging weapon: hands %s type %s anc %s" % (out["hands"], out["type"], out["anc"]))
        self.assertIn("%d frames." % out["fpa"], out["amaIas"] or "", "the attack step is not _cbFpa: %s" % out["amaIas"])
        self.assertNotEqual(out["fpa"], out["fpaWrong"], "the planted attack formula matched _cbFpa, so this check cannot see a drift")
        self.assertNotIn("%d frames." % out["fpaWrong"], (out["amaIas"] or "").split(". ")[0] + ".")
        self.assertEqual(out["druFhr"]["value"], {"min": 0, "max": 0})
        self.assertIn("13 frames.", out["druBare"] or "")
        self.assertEqual(out["druSwordFhr"]["value"], {"min": 0, "max": 0})
        self.assertIn("14 frames.", out["druSword"] or "")
        self.assertTrue(out["shael"], "Shael is not in the rune table")
        self.assertIn("Increased Attack Speed", out["offLines"] or "", "a Shael in the off hand was not read as a weapon: %s" % out["offLines"])
        self.assertNotIn("Faster Hit Recovery", out["offLines"] or "")
        self.assertTrue(out["twoName"], "no one-or-two-handed weapon is in the database")
        self.assertIn("one hand or two", out["barbIas"] or "")
        self.assertNotRegex(out["barbIas"] or "", r"\d+ frames")
        self.assertIn("frames.", out["amaTwo"] or "", "a two-handed weapon on an Amazon stayed unknown: %s" % out["amaTwo"])
        self.assertNotIn("one hand or two", out["amaTwo"] or "")
        self.assertFalse(out["owed"])

    def test_a_shimmering_charm_and_a_worn_item_count_once_the_level_can_use_them(self):
        """A level 1 Paladin in Hell keeps the penalty. The charm's tooltip still shows its mods.
        At the charm's required level the typed all-resist and of Balance move the same rows.
        A worn magic shield and a worn magic armor follow that same level line."""
        out = JOIN._run(r"""
          function bpOf(label){
            var h = statsHtml(), i = h.indexOf('<span class="cb-sl">' + label + '</span>');
            if (i < 0) return null;
            var row = h.slice(i, h.indexOf('</div>', i)), j = row.indexOf('class="cb-bp"');
            if (j < 0) return '';
            return row.slice(row.indexOf('>', j) + 1, row.indexOf('</span>', j));
          }
          function valOf(key){
            var eb = window._cbEngineBuild(cur()), st = window._cbState();
            var sh = window.D2R_CHAR_ENGINE.sheet(eb.build, { difficulty: st.diff, quests: !!st.quests });
            var r = sh.rows.filter(function(x){ return x.key === key; })[0];
            return r ? { value: r.value, source: r.source } : null;
          }
          function notes(){
            var h = statsHtml(), out = [], from = 0;
            while (true){
              var i = h.indexOf('cb-st-note', from); if (i < 0) break;
              var a = h.indexOf('>', i), z = h.indexOf('</div>', a);
              out.push(strip(h.slice(a + 1, z))); from = z;
            }
            return out;
          }
          function typeAx(ax, key, lo, hi, v){
            window._cbRollInput({ target: {
              value: String(v),
              classList: { contains: function(c){ return c === 'cb-roll'; }, add: function(){}, remove: function(){}, toggle: function(){} },
              getAttribute: function(a){
                var at = { 'data-key': key, 'data-lo': String(lo), 'data-hi': String(hi), 'data-ax': String(ax) };
                return at[a] == null ? null : at[a];
              }
            }});
            return window._cbState().modSay || '';
          }
          mk('Paladin', 1);
          window._cbOpenPick('inv', null, [0, 0]); window._cbChoose('b:cm1');
          OUT.addShim = window._cbAddMod('p322');
          OUT.typed = typeAx(0, 'm1', 3, 5, 5);
          OUT.addBal = window._cbAddMod('s267');
          var e = cur().sets[0].inv[0], it = window._cbItem(e.id);
          var tip = window._cbTipEntry(e, it, 1, 'inv', 'Paladin');
          OUT.tip = (tip.lines || []).map(function(l){ return strip(l.html != null ? l.html : l.t); });
          OUT.req = tip.reqs && tip.reqs.lvl;
          window._cbClosePick();
          OUT.fire1 = valOf('res-fire'); OUT.cold1 = valOf('res-cold');
          OUT.light1 = valOf('res-ltng'); OUT.pois1 = valOf('res-pois');
          OUT.fhr1 = valOf('fhr'); OUT.step1 = bpOf('Faster Hit Recovery'); OUT.notes1 = notes();
          window._cbSetField('level', 28);
          OUT.fire28 = valOf('res-fire'); OUT.fhr28 = valOf('fhr'); OUT.notes28 = notes();
          window._cbSetField('level', 29);
          OUT.fire29 = valOf('res-fire'); OUT.cold29 = valOf('res-cold');
          OUT.light29 = valOf('res-ltng'); OUT.pois29 = valOf('res-pois');
          OUT.fhr29 = valOf('fhr'); OUT.step29 = bpOf('Faster Hit Recovery'); OUT.notes29 = notes();
          mk('Paladin', 1);
          window._cbOpenPick('slot', 'larm');
          OUT.buck = window._cbChoose('b:buc') && window._cbQuality('m') && window._cbAddMod('p323');
          OUT.buckTyped = typeAx(0, 'm1', 3, 7, 5);
          window._cbClosePick();
          OUT.buckFire1 = valOf('res-fire'); OUT.buckNotes1 = notes();
          window._cbSetField('level', 4);
          OUT.buckFire4 = valOf('res-fire'); OUT.buckFhr4 = valOf('fhr'); OUT.buckNotes4 = notes();
          mk('Paladin', 1);
          window._cbOpenPick('slot', 'tors');
          OUT.arm = window._cbChoose('b:qui') && window._cbQuality('m') && window._cbAddMod('s262');
          window._cbClosePick();
          OUT.armFhr1 = valOf('fhr'); OUT.armFire1 = valOf('res-fire'); OUT.armNotes1 = notes();
          window._cbSetField('level', 3);
          OUT.armFhr3 = valOf('fhr'); OUT.armStep3 = bpOf('Faster Hit Recovery'); OUT.armNotes3 = notes();
        """)
        self.assertTrue(out["addShim"] and out["addBal"], "the charm did not take Shimmering and of Balance")
        self.assertEqual(out["typed"], "saved: 5 (EXACT)")
        self.assertEqual(out["req"], 29)
        self.assertEqual(out["tip"], ["+5% Faster Hit Recovery", "All Resistances +5"])
        bare = {"value": {"min": -70, "max": -70}, "source": "EXACT"}
        zero = {"value": {"min": 0, "max": 0}, "source": "EXACT"}
        self.assertEqual(out["fire1"], bare)
        self.assertEqual(out["cold1"], bare)
        self.assertEqual(out["light1"], bare)
        self.assertEqual(out["pois1"], bare)
        self.assertEqual(out["fhr1"], zero)
        self.assertEqual(out["step1"], "9 frames. +7% more reaches the next step.")
        self.assertIn("needs level 29 - a level 1 character gets nothing from it", " ".join(out["notes1"]))
        self.assertEqual(out["fire28"], bare, "one level under the requirement still counted the charm")
        self.assertEqual(out["fhr28"], zero)
        self.assertIn("needs level 29 - a level 28 character gets nothing from it", " ".join(out["notes28"]))
        moved = {"value": {"min": -65, "max": -65}, "source": "EXACT"}
        self.assertEqual(out["fire29"], moved)
        self.assertEqual(out["cold29"], moved)
        self.assertEqual(out["light29"], moved)
        self.assertEqual(out["pois29"], moved)
        self.assertEqual(out["fhr29"], {"value": {"min": 5, "max": 5}, "source": "EXACT"})
        self.assertEqual(out["step29"], "9 frames. +2% more reaches the next step.")
        self.assertEqual(out["notes29"], [])
        self.assertTrue(out["buck"], "the buckler did not take Shimmering: %s" % out.get("buckTyped"))
        self.assertEqual(out["buckTyped"], "saved: 5 (EXACT)")
        self.assertEqual(out["buckFire1"], bare)
        self.assertIn("needs level 4 - a level 1 character gets nothing from it", " ".join(out["buckNotes1"]))
        self.assertEqual(out["buckFire4"], moved, "a worn Shimmering shield did not move fire resistance: %s" % out["buckFire4"])
        self.assertEqual(out["buckFhr4"], zero, "the shield has no faster hit recovery and the row moved")
        self.assertEqual(out["buckNotes4"], [])
        self.assertTrue(out["arm"], "Quilted Armor did not take of Balance")
        self.assertEqual(out["armFire1"], bare)
        self.assertEqual(out["armFhr1"], zero)
        self.assertIn("needs level 3 - a level 1 character gets nothing from it", " ".join(out["armNotes1"]))
        self.assertEqual(out["armFhr3"], {"value": {"min": 10, "max": 10}, "source": "EXACT"})
        self.assertEqual(out["armStep3"], "8 frames. +5% more reaches the next step.")
        self.assertEqual(out["armNotes3"], [])


RED_PROOF = [
    {
        "why": "v3889 (GrokBot 6734314659) - a build with no class says its class has no published table again",
        "file": "bible.html",
        "find": "    if (!row && !cls) return { unknown: true, noClass: true, why: 'No class is chosen yet, so the ' + kind.toUpperCase() + ' steps are not known.' };\n",
        "replace": "",
        "matches": 1,
    },
    {
        "why": "the Druid casting base is put back to the printed 16, so 0% is no longer the published 18 frames",
        "file": "bible.html",
        "find": "Druid: [15, 208]",
        "replace": "Druid: [16, 208]",
        "matches": 1,
    },
    {
        "why": "Increased Attack Speed stops asking _cbFpa and paints 99 frames",
        "file": "bible.html",
        "find": "var f0 = _cbFpa(frames, rate, ias, wsm);",
        "replace": "var f0 = 99;",
        "matches": 1,
    },
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
