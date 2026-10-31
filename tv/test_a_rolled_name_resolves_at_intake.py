# -*- coding: utf-8 -*-
"""v3849 - A ROLLED NAME TAKES ITS TYPE FROM THE GAME'S SUFFIX TABLE AT INTAKE.

The jewelry hand-pool (RARE_NAME_POOLS) stays the floor it already is: a Whorl is still asked
"ring or jewel?" and an Eye is still the Jewel that pool draws. This law reads CB_DB rn, the
rareprefix / raresuffix rows, and says what those rows actually are:

  Band, Coil, Loop, Spiral, Circle     ring
  Finger, Grip, Hold                   glov + ring     (not ring only)
  Whorl                                ring + orb + jewl  (not ring only)
  Nails                                boot + spea + pole (not ring)
  Eye                                  misc            (not jewl)
  Harness                              belt
  Song                                 weap            (a category, not a base)

A magic name is a magic prefix, a known base, and an "of ..." suffix: "Artisan's Spired Helm of
the Mammoth" routes by Spired Helm. Deckard Cain, Tyrael and Stash are refused; Tyrael's Might is
not. An unresolved ring/jewel draws the question and not the white-box fallback glyph.
"""
import json
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable
enable()
from cb_node_harness import NODE  # noqa: E402

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
DIAMOND = "\u25c6"


def _src():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def _between(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("anchor %r matched %d times" % (start[:48], src.count(start)))
    i = src.index(start)
    j = src.index(end, i)
    if j < 0:
        raise AssertionError("end anchor missing: %r" % end[:48])
    return src[i:j + len(end)]


def _run(js):
    if NODE is None:
        raise AssertionError("node is not on this machine - this law does not skip")
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    if r.returncode != 0:
        raise AssertionError("node refused the intake grammar: %s" % (r.stderr or "")[-800:])
    line = (r.stdout or "").strip().splitlines()
    if not line:
        raise AssertionError("node printed nothing: %s" % (r.stderr or "")[-400:])
    return json.loads(line[-1])


def _program():
    src = _src()
    i = src.index('id="cb-db">') + len('id="cb-db">')
    db = src[i:src.index("</script>", i)]
    grammar = _between(src, "const RARE_NAME_POOLS = {", "window._intakeRoute = _intakeRoute;\n")
    art = _between(src, "function artOr(name, fallbackHtml, size){", "window._artRolledBase = _artRolledBase;")
    a = src.index("  var _NOT_ITEMS = {")
    if src.count("  var _NOT_ITEMS = {") != 1:
        raise AssertionError("the NPC denylist anchor is not unique")
    deny = src[a:src.index("  window.tvVaultRegister = function(name, witness){", a)]
    rs = src.index("      var _rq = (!base && typeof _rolledQuality === 'function') ? _rolledQuality(name) : null;")
    re_ = src.index("        if (_inRoute) return _inRoute;", rs)
    route = src[rs:src.index("\n", src.index("\n", re_) + 1) + 1]
    ss = src.index("          var _stamp = (typeof window._intakeStamp === 'function')")
    stamp = "\n".join(src[ss:].splitlines()[:3]) + "\n"
    return r"""
var window = {};
var ITEM_VALUE = null;
function d2rItemLookup(){ return null; }
function artUrl(n){
  var k = String(n || '');
  if (k === 'Belt' || k === 'Spired Helm' || k === 'Ring' || k === 'Jewel' || k === 'Gloves') return 'art/test-' + k + '.png';
  return null;
}
function _artRarity(){ return ''; }
function _d2artEsc(s){ return String(s == null ? '' : s); }
function _artSlotClean(n){ return String(n == null ? '' : n).replace(/\s*\([^)]*\)\s*$/, '').trim(); }
function muleById(id){ return id === 'magic-rare' ? { id: id } : null; }
%s
%s
%s
window._cbDb = function(){ return %s; };
function routeTail(name){
  var base = null;
%s
  return null;
}
function stampOf(name){
  var _rq1 = (typeof _rolledQuality === 'function') ? _rolledQuality(name) : null;
%s
  return _tvEntry;
}
function one(n){ return _intakeResolve(n); }
var ask = ['Raven Whorl','Viper Eye','Grim Harness','Bramble Song','Grim Nails','Raven Finger','Raven Grip','Raven Hold','Chaos Band','Bitter Coil','Death Loop','Grim Spiral','Rune Circle'];
var got = {};
ask.forEach(function(n){ got[n] = one(n); });
got["Artisan's Spired Helm of the Mammoth"] = one("Artisan's Spired Helm of the Mammoth");
got['Artisan helm'] = one("Artisan's Spired Helm");
got['helm of'] = one('Spired Helm of the Mammoth');
got['plain helm'] = one('Spired Helm');
got['Viper Eye Jewel'] = one('Viper Eye Jewel');
got['Viper Eye Spired Helm'] = one('Viper Eye Spired Helm');
got['not a base'] = one("Artisan's Not A Base of the Mammoth");
got['Deckard Cain'] = one('Deckard Cain');
got['Tyrael'] = one('Tyrael');
got['Stash'] = one('Stash');
got["Tyrael's Might"] = one("Tyrael's Might");
got["Gheed's Fortune"] = one("Gheed's Fortune");
window.ITEM_VALUE = { 'Raven Claw': 1 };
got['Raven Claw'] = one('Raven Claw');
window.ITEM_VALUE = null;
var out = {
  got: got,
  art: {
    whorl: artOr('Raven Whorl', '\u25c6', 'lg'),
    gyre: artOr('Raven Gyre', '\u25c6', 'lg'),
    harness: artOr('Grim Harness', '\u25c6', 'lg'),
    helm: artOr("Artisan's Spired Helm of the Mammoth", '\u25c6', 'lg'),
    song: artOr('Bramble Song', '\u25c6', 'lg')
  },
  route: {
    whorl: routeTail('Raven Whorl'),
    gyre: routeTail('Raven Gyre'),
    harness: routeTail('Grim Harness'),
    helm: routeTail("Artisan's Spired Helm of the Mammoth"),
    eye: routeTail('Viper Eye'),
    song: routeTail('Bramble Song'),
    nails: routeTail('Grim Nails')
  },
  stamp: {
    harness: stampOf('Grim Harness'),
    eye: stampOf('Doom Eye'),
    whorl: stampOf('Raven Whorl'),
    helm: stampOf("Artisan's Spired Helm of the Mammoth")
  }
};
console.log(JSON.stringify(out));
""" % (grammar, art, deny, db, route, stamp)


class RolledNameResolvesAtIntake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = _run(_program())

    def test_a_missing_node_fails_the_law(self):
        global NODE
        saved = NODE
        NODE = None
        try:
            try:
                _run("console.log('[]')")
            except AssertionError as e:
                self.assertIn("does not skip", str(e))
            except unittest.SkipTest:
                self.fail("a missing node skipped the law")
            else:
                self.fail("a missing node did not fail the law")
        finally:
            NODE = saved

    def test_the_suffix_table_is_what_the_rows_say(self):
        g = self.o["got"]
        rings = ["Chaos Band", "Bitter Coil", "Death Loop", "Grim Spiral", "Rune Circle"]
        for n in rings:
            self.assertEqual(g[n]["types"], ["Ring"], n)
            self.assertEqual(g[n]["base"], "Ring", n)
        for n in ("Raven Finger", "Raven Grip", "Raven Hold"):
            self.assertEqual(g[n]["types"], ["Gloves", "Ring"], n)
            self.assertIsNone(g[n]["base"], n)
        self.assertEqual(g["Raven Whorl"]["itypes"], ["ring", "orb", "jewl"])
        self.assertEqual(g["Raven Whorl"]["types"], ["Ring", "Orb", "Jewel"])
        self.assertIsNone(g["Raven Whorl"]["base"])
        self.assertEqual(g["Grim Nails"]["itypes"], ["boot", "spea", "pole"])
        self.assertEqual(g["Grim Nails"]["types"], ["Boots", "Spear", "Polearm"])
        self.assertNotIn("Ring", g["Grim Nails"]["types"])
        self.assertIsNone(g["Grim Nails"]["base"])
        self.assertEqual(g["Viper Eye"]["itypes"], ["misc"])
        self.assertEqual(g["Viper Eye"]["types"], [])
        self.assertIsNone(g["Viper Eye"]["base"])
        self.assertNotEqual(g["Viper Eye"]["base"], "Jewel")
        self.assertEqual(g["Grim Harness"]["itypes"], ["belt"])
        self.assertEqual(g["Grim Harness"]["types"], ["Belt"])
        self.assertEqual(g["Grim Harness"]["base"], "Belt")
        self.assertEqual(g["Bramble Song"]["itypes"], ["weap"])
        self.assertEqual(g["Bramble Song"]["types"], [])
        self.assertIsNone(g["Bramble Song"]["base"])

    def test_a_magic_name_routes_by_its_base(self):
        g = self.o["got"]
        helm = g["Artisan's Spired Helm of the Mammoth"]
        self.assertEqual(helm["q"], "magic")
        self.assertEqual(helm["base"], "Spired Helm")
        self.assertEqual(g["Artisan helm"]["base"], "Spired Helm")
        self.assertEqual(g["helm of"]["base"], "Spired Helm")
        self.assertIsNone(g["plain helm"]["q"])
        self.assertIsNone(g["not a base"]["q"])
        self.assertEqual(self.o["route"]["helm"]["id"], "magic-rare")
        self.assertIn("spired helm", self.o["route"]["helm"]["why"])
        self.assertEqual(self.o["stamp"]["helm"]["base"], "Spired Helm")
        self.assertEqual(self.o["stamp"]["helm"]["rarity"], "magic")
        self.assertIn("art/test-Spired Helm.png", self.o["art"]["helm"])

    def test_intake_files_a_table_rare_and_keeps_the_hand_pool_floor(self):
        r = self.o["route"]
        self.assertEqual(r["harness"]["id"], "magic-rare")
        self.assertEqual(r["harness"]["base"], "Belt")
        self.assertIn("belt", r["harness"]["why"])
        self.assertEqual(self.o["stamp"]["harness"]["base"], "Belt")
        self.assertEqual(self.o["stamp"]["harness"]["rarity"], "rare")
        self.assertIn("art/test-Belt.png", self.o["art"]["harness"])
        self.assertNotIn("d2art-wrap lg d2art-failed", self.o["art"]["harness"])
        # v3849 Elad 11:43-11:44: "Raven Whorl IS a ring" - his ruling; Gyre keeps the ring / jewel question
        self.assertIn("Raven + Whorl: ring)", r["whorl"]["why"])
        self.assertIn("ring / jewel", r["gyre"]["why"])
        self.assertNotIn("orb", r["gyre"]["why"])
        self.assertEqual(self.o["stamp"]["whorl"]["base"], "Raven Whorl")
        self.assertEqual(self.o["stamp"]["whorl"]["rarity"], "rare")
        self.assertIn("jewel", r["eye"]["why"])
        self.assertEqual(self.o["stamp"]["eye"]["base"], "Doom Eye")
        self.assertEqual(self.o["stamp"]["eye"]["rarity"], "rare")
        self.assertIsNone(r["song"]["base"])
        self.assertIn("itype weap", r["song"]["why"])
        self.assertIsNone(r["nails"]["base"])
        self.assertNotIn("ring", r["nails"]["why"])

    def test_an_unresolved_ring_or_jewel_draws_no_white_box(self):
        html = self.o["art"]["gyre"]
        self.assertIn("d2art-failed", html)
        self.assertIn("ring or jewel", html)
        self.assertNotIn("orb", html)
        self.assertNotIn("src=", html)
        self.assertNotIn(DIAMOND, html)
        self.assertNotIn("<img", html)

    def test_an_npc_or_a_panel_word_is_refused_and_a_real_item_is_not(self):
        g = self.o["got"]
        for n in ("Deckard Cain", "Tyrael", "Stash"):
            self.assertEqual(g[n]["refused"], "not-an-item", n)
            self.assertFalse(g[n]["ok"], n)
        self.assertIsNone(g["Tyrael's Might"]["refused"])
        self.assertTrue(g["Tyrael's Might"]["ok"])
        self.assertIsNone(g["Gheed's Fortune"]["refused"])
        self.assertTrue(g["Raven Claw"]["known"])
        self.assertIsNone(g["Raven Claw"]["q"])

    def test_a_rare_read_with_its_base_line_is_that_base(self):
        g = self.o["got"]
        self.assertEqual((g["Viper Eye Jewel"]["q"], g["Viper Eye Jewel"]["base"]), ("rare", "Jewel"), g["Viper Eye Jewel"])
        self.assertIsNone(g["Viper Eye Spired Helm"]["q"], "an Eye suffix does not roll on a helm, so the name is not a rare helm")

    def test_raven_whorl_is_a_ring_by_his_ruling(self):
        html = self.o["art"]["whorl"]
        self.assertIn('src="art/test-Ring.png"', html, "Raven Whorl draws no ring art (the white box Elad saw)")
        self.assertNotIn("ring or jewel", html)

    def test_a_weapon_category_draws_no_invented_base(self):
        html = self.o["art"]["song"]
        self.assertNotIn("src=", html)
        self.assertNotIn("art/test-", html)


RED_PROOF = [
    {"why": "v3849 - a rare read with its base line glued on (Viper Eye Jewel) stays in the Unsorted dock",
     "file": "bible.html",
     "find": "  if (!magSuf && _rp.length === 2){",
     "replace": "  if (false){",
     "matches": 1},
    {"why": "v3849 - a Whorl is a ring-or-jewel question again (Raven Whorl the white box)",
     "file": "bible.html",
     "find": "  Jewel:  ['Gyre','Talisman','Heart','Scarab','Eye'],",
     "replace": "  Jewel:  ['Gyre','Whorl','Talisman','Heart','Scarab','Eye'],",
     "matches": 1},
    {"why": "v3849 - an unresolved ring/jewel paints the white-box fallback glyph again",
     "file": "bible.html",
     "find": "var _askBox = (_ask && /\\bring\\b/i.test(String(_ask)) && /\\bjewel\\b/i.test(String(_ask))) ? '' : (fallbackHtml || '');\n",
     "replace": "var _askBox = (fallbackHtml || '');\n",
     "matches": 1},
    {"why": "v3849 - one suffix type is no longer the intake base (Grim Harness stays unnamed)",
     "file": "bible.html",
     "find": "base: types.length === 1 ? types[0] : null",
     "replace": "base: null",
     "matches": 1},
    {"why": "v3849 - a magic name is not split into its base",
     "file": "bible.html",
     "find": "var hit = _findBase(d, nm);",
     "replace": "var hit = null;",
     "matches": 1},
    {"why": "v3849 - an NPC word is no longer refused at intake",
     "file": "bible.html",
     "find": "var refused = (typeof window !== 'undefined' && typeof window._vaultNotAnItem === 'function') ? window._vaultNotAnItem(nm) : null;",
     "replace": "var refused = null;",
     "matches": 1},
    {"why": "v3849 - a catalogue unique is read as a rolled rare (Raven Claw)",
     "file": "bible.html",
     "find": "try { if (typeof _rareRealName === 'function' && _rareRealName(nm)) return { ok: true, q: null, base: null, types: [], itypes: [], refused: null, why: null, known: true }; } catch (eRn) {}",
     "replace": "try { if (false) return null; } catch (eRn) {}",
     "matches": 1},
    {"why": "v3849 - the router no longer files a table rare the jewelry pool does not know",
     "file": "bible.html",
     "find": "if (!_rq && typeof window._intakeRoute === 'function' && muleById('magic-rare')){",
     "replace": "if (false && typeof window._intakeRoute === 'function' && muleById('magic-rare')){",
     "matches": 1},
    {"why": "v3849 - the register stamps the raw name over the resolved base",
     "file": "bible.html",
     "find": "_stamp.base || name",
     "replace": "name",
     "matches": 1},
    {"why": "v3849 - art no longer reads a table base the jewelry pool did not name",
     "file": "bible.html",
     "find": "if (_irB && _irB.base) out.base = String(_irB.base);",
     "replace": "if (false && _irB && _irB.base) out.base = String(_irB.base);",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
