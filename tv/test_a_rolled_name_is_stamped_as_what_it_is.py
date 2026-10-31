# -*- coding: utf-8 -*-
"""#269 (REG-2054) - A ROLLED NAME IS STAMPED AS WHAT IT IS: ONE GRAMMAR FOR THE ROUTER AND BOTH TV STUB WRITERS.

GrokBot ticks 411-418 on #230: Dread Grasp and Storm Scarab tipped "Base item · TV-vaulted · Not a grail item", and the
magic grand charms Chaotic Grand Charm of Greed, Grand Charm of Inertia and Steel Grand Charm of Balance sat in UNI-SMALL
as "Base item … Best-of-the-best — rivals runewords / uniques" while MAGIC & RARE was empty. The router knew the rare
grammar (REG-2024); the two stub writers stamped rarity:'basic' for every name no catalogue knew.

  * _rolledQuality: the exact two-word rare shape (a RarePrefix + a RareSuffix, the game's tables) -> rare; a charm /
    jewel / ring / amulet wearing a prefix and/or an "of ..." suffix -> magic with its base; a bare base, a unique's own
    name and any name a catalogue knows -> null;
  * the router files a magic small item to MAGIC & RARE; both stub writers stamp the rolled quality;
  * a TV stub's tip reads Magic / Rare (an old 'basic' stub included, derived at read time) and never calls itself
    "Best-of-the-best" - that line belongs to curated reference profiles.
Drives the SHIPPED _rolledQuality (with the game's real rare tables) and _extraTipHtml, cut from bible.html and run in
node. A missing node raises; this law does not skip.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable as _console_safe_enable  # noqa: E402
_console_safe_enable()
from cb_node_harness import NODE  # noqa: E402

PAGE = os.path.join(os.path.dirname(HERE), "bible.html")
TABLES = ("const RARE_NAME_POOLS = {", "\nwindow.RARE_NAME_POOLS = RARE_NAME_POOLS;")
HELPER = ("var _MAGIC_SMALL_RE = ", "\nwindow._rolledQuality = _rolledQuality;\n")
TIP = ("function _extraTipHtml(nm){\n", "Not a grail item: the chronicle does not count it.</div>';\n}\n")
# v3849 (grok/v3849-b): the stub asks _intakeStamp, which asks _rolledQuality first and the suffix tables second
STUB1 = "var _tvEntry = { rarity: _stamp.rarity || 'basic', base: _stamp.base || name, cat:'📺 TV-vaulted', val:'tv',"
STAMP = "  try { rq = (typeof _rolledQuality === 'function') ? _rolledQuality(name) : null; } catch (eRq) { rq = null; }\n"
STUB2 = "window._tvExtraRemember(n, { rarity: _rq2 ? _rq2.q : 'basic', base: (_rq2 && _rq2.base) ? _rq2.base : n,"
ROUTER = "      if (_rq && _rq.q === 'magic' && muleById('magic-rare'))\n"


def _src():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def _cut(s, pair):
    start, end = pair
    if s.count(start) != 1:
        raise AssertionError("anchor %r matched %d times - re-point this law" % (start[:50], s.count(start)))
    i = s.index(start)
    return s[i:s.index(end, i) + len(end)]


def _node(body):
    if NODE is None:
        raise AssertionError("node is not on this machine - this gate does not skip")
    s = _src()
    js = """
var window = {};
// "Blood Spiral" WEARS the rare grammar in the game's real tables (a RarePrefix + a ring suffix); the stub makes it a
// catalogue name, so only the catalogue guard can decline it - heart2 measured "Raven Frost" (no ring suffix) proving nothing
function d2rItemLookup(n){ return n === "Blood Spiral" ? { n: n } : null; }
%s
%s
var _Q_LABEL = { basic: 'Base item' };
function _craftBuffsHtml(){ return ''; }
var EXTRA_ITEMS = {
  "Chaotic Grand Charm of Greed": { rarity: 'basic', base: "Chaotic Grand Charm of Greed", cat: 'TV-vaulted', val: 'tv' },
  "Dread Grasp": { rarity: 'rare', base: 'Dread Grasp', cat: 'TV-vaulted', val: 'tv' },
  "Curated Thing": { rarity: 'crafted', base: 'Amulet', cat: 'High-Value Finds', val: 'high' } };
%s
%s
""" % (_cut(s, TABLES), _cut(s, HELPER), _cut(s, TIP), body)
    # the program goes in on STDIN - a law never hands node its program on argv
    r = subprocess.run([NODE, "-"], input=js, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise AssertionError("the cut functions did not run in node: %s" % r.stderr[-600:])
    return json.loads(r.stdout.strip().splitlines()[-1])


class ARolledNameIsStampedAsWhatItIs(unittest.TestCase):

    def test_the_grammar_names_rares_and_magic_small_items_and_nothing_else(self):
        names = ["Dread Grasp", "Storm Scarab", "Chaotic Grand Charm of Greed", "Grand Charm of Inertia",
                 "Steel Grand Charm of Balance", "Grand Charm", "Gheed's Fortune", "Blood Spiral", "Annihilus"]
        got = _node("var O = {}; %s.forEach(function(n){ O[n] = _rolledQuality(n); }); console.log(JSON.stringify(O));"
                    % json.dumps(names))
        self.assertEqual((got["Dread Grasp"] or {}).get("q"), "rare", got["Dread Grasp"])
        self.assertEqual((got["Storm Scarab"] or {}).get("q"), "rare", got["Storm Scarab"])
        for n in ("Chaotic Grand Charm of Greed", "Grand Charm of Inertia", "Steel Grand Charm of Balance"):
            self.assertEqual((got[n] or {}).get("q"), "magic", "%s: %r" % (n, got[n]))
            self.assertEqual(got[n].get("base"), "Grand Charm", got[n])
        for n in ("Grand Charm", "Gheed's Fortune", "Annihilus"):
            self.assertIsNone(got[n], "%s was given a rolled quality: %r" % (n, got[n]))
        self.assertIsNone(got["Blood Spiral"], "a name the catalogue knows wore the rare grammar")

    def test_a_tv_stub_tip_says_what_the_name_is_and_never_best_of_the_best(self):
        got = _node("console.log(JSON.stringify({ m: _extraTipHtml('Chaotic Grand Charm of Greed'), "
                    "r: _extraTipHtml('Dread Grasp'), c: _extraTipHtml('Curated Thing') }));")
        self.assertIn("Magic &middot; Grand Charm", got["m"], "an old 'basic' magic stub still tips as a base item")
        self.assertNotIn("Base item", got["m"])
        self.assertNotIn("Best-of-the-best", got["m"], "a TV-registered stub calls itself best-of-the-best")
        self.assertNotIn("Best-of-the-best", got["r"])
        self.assertIn("Best-of-the-best", got["c"], "a curated reference profile lost its line")

    def test_the_router_and_both_stub_writers_ask_the_grammar(self):
        s = _src()
        self.assertEqual(s.count(ROUTER), 1, "the router no longer files a magic small item to MAGIC & RARE")
        self.assertEqual(s.count(STUB1), 1, "tvVaultRegister's stub no longer stamps the rolled quality")
        self.assertEqual(s.count(STAMP), 1, "the intake stamp no longer asks the rolled-name grammar first")
        self.assertEqual(s.count(STUB2), 1, "the chronicle-apply stub no longer stamps the rolled quality")


RED_PROOF = [
    {"why": "REG-2054 - a magic charm is no rolled name again (filed as a base item in UNI-SMALL)",
     "file": "bible.html",
     "find": "  if (m && (m[1] || m[3])) return { q: 'magic', base: m[2] };\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2054 - a bare base wears the magic grammar",
     "file": "bible.html",
     "find": "  if (m && (m[1] || m[3])) return { q: 'magic', base: m[2] };\n",
     "replace": "  if (m) return { q: 'magic', base: m[2] };\n",
     "matches": 1},
    {"why": "REG-2054 - a name the catalogue knows wears the rare grammar",
     "file": "bible.html",
     "find": "  try { if (typeof d2rItemLookup === 'function' && d2rItemLookup(nm)) return null; } catch(e){}\n",
     "replace": "",
     "matches": 1},
    {"why": "REG-2054 - an old basic stub still tips as a base item",
     "file": "bible.html",
     "find": "  if (e.val === 'tv' && rar === 'basic' && typeof _rolledQuality === 'function'){\n",
     "replace": "  if (false){\n",
     "matches": 1},
    {"why": "REG-2054 - a TV stub calls itself best-of-the-best again",
     "file": "bible.html",
     "find": "(e.val === 'tv' ? '' : 'Best-of-the-best — rivals runewords / uniques. ')",
     "replace": "('Best-of-the-best — rivals runewords / uniques. ')",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=1)
