#!/usr/bin/env python3
"""The Uniques tally names every hunt card, and nothing the file does not contain.

Measured 2026-11-01 from uniqueitems.txt. A chronicle row is spawnable==1 and
disableChronicle!=1. That file count is 403. Rainbow Facet is eight of them. Six
quest uniques are in that file and are not cards. The hunt list and the pin are
the same 397. Polaris Spear and The Scourge are not in the file. The six
colossal jewels have spawnable blank, so they stay outside the file count and tick on
their own drawer.

The roster is a different surface. This law drives the tally function, then checks
the tick writer actually accepts a tally name the roster does not carry.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
try:
    from console_safe import enable
    enable()
except Exception:
    pass

BIBLE = os.path.join(os.path.dirname(HERE), "bible.html")
ROSTER = os.path.join(HERE, "unique_roster.json")

BLOCK_START = "  var _CHRON_FACETS = ["
BLOCK_END = "  window._chronicleTickName = _chronicleTickName;"
PRED_START = "  var _CHRON_SUNDER_BASES = ["
PRED_END = "  window._isUpgradedSunder = _isUpgradedSunder;"

FACETS = [
    "Rainbow Facet (Lightning, on Death) — level 47 Chain Lightning",
    "Rainbow Facet (Cold, on Death) — level 37 Blizzard",
    "Rainbow Facet (Fire, on Death) — level 31 Meteor",
    "Rainbow Facet (Poison, on Death) — level 51 Poison Nova",
    "Rainbow Facet (Lightning, on Level-up) — level 41 Nova",
    "Rainbow Facet (Cold, on Level-up) — level 43 Frost Nova",
    "Rainbow Facet (Fire, on Level-up) — level 29 Blaze",
    "Rainbow Facet (Poison, on Level-up) — level 23 Venom",
]
QUESTS = [
    "Amulet of the Viper", "Staff of Kings", "Horadric Staff",
    "Hell Forge Hammer", "Khalim's Flail", "Khalim's Will",
]
COLOSSAL = [
    "Defender's Bile", "Guardian's Thunder", "Protector's Frost",
    "Defender's Fire", "Protector's Stone", "Guardian's Light",
]
BARE_SUNDERS = [
    "Bone Break", "Cold Rupture", "Crack of the Heavens",
    "Flame Rift", "Rotting Fissure", "Black Cleft",
]


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _between(src, start, end, what):
    i = src.find(start)
    assert i >= 0, "%s: opening anchor is gone" % what
    assert src.find(start, i + 1) < 0, "%s: opening anchor is not unique" % what
    j = src.find(end, i)
    assert j > i, "%s: closing anchor is gone" % what
    return src[i:j + len(end)]


HARNESS = r"""
var window = {};
%(pred)s
%(block)s

var roster = %(roster)s;
var folded = roster.filter(function(n){ return !_isUpgradedSunder(n); });
var tally = _chronicleNameList(folded);
var col = _colossalTallyRows();

function ownedHas(own, n){
  if (own.has(n)) return true;
  if (_chronicleIndexHit(own, n)) return true;
  if (_chronicleStopResolver(n)) return false;
  return false;
}

var bare = new Set(["Rainbow Facet"]);
var deaths = new Set(["Deaths's Web"]);
var helm = new Set(["Unique Warlock Helm"]);
var precraft = new Set(["PreCrafted Bone Break"]);
var facetHits = %(facets)s.filter(function(n){ return ownedHas(bare, n); });

console.log(JSON.stringify({
  tally: tally,
  colossal: col.map(function(x){ return x.n; }),
  colQ: col.map(function(x){ return x.qlvl; }),
  facetHits: facetHits,
  deathsWeb: ownedHas(deaths, "Death's Web"),
  deathsFathom: ownedHas(deaths, "Death's Fathom"),
  helm: ownedHas(helm, "Hellwarden's Will"),
  precraftAlias: (_CHRON_SUNDER_ALIASES["Bone Break"] || []).indexOf("PreCrafted Bone Break") >= 0,
  precraftIsUpgraded: _isUpgradedSunder("PreCrafted Bone Break"),
  bareIsUpgraded: _isUpgradedSunder("Bone Break"),
  tickFacet: _chronicleTickName(%(facets)s[6]),
  tickQuest: _chronicleTickName("Khalim's Will"),
  questSneaks: _chronicleNameList(folded.concat(["Khalim's Will"])).indexOf("Khalim's Will") >= 0,
  questInBase: %(quests)s.filter(function(n){ return !!_CHRON_BASE[n]; }),
  tickCol: _chronicleTickName("Guardian's Thunder"),
  tickBareFacet: _chronicleTickName("Rainbow Facet"),
  tickPolaris: _chronicleTickName("Polaris Spear"),
  tickGull: _chronicleTickName("Gull"),
  khalimKey: _chronicleIndexHit(new Set(["KhalimFlail"]), "Khalim's Flail"),
  baseMiss: tally.filter(function(n){ return !_CHRON_BASE[n]; }),
  felloak: _CHRON_BASE["Felloak"],
  gull: _CHRON_BASE["Gull"],
  blink: _CHRON_BASE["Blinkbat's Form"],
  broc: _CHRON_BASE["The Hand of Broc"],
  heavens: _CHRON_BASE["Heaven's Light"],
  redeemer: _CHRON_BASE["The Redeemer"],
  tyrael: _CHRON_BASE["Tyrael's Might"],
  templar: _CHRON_BASE["Templar's Might"],
  storm: _CHRON_BASE["Stormlash"],
  horizon: _CHRON_BASE["Horizon's Tornado"],
  bane: _CHRON_BASE["Bane Ash"],
  web: _CHRON_BASE["Death's Web"],
  earth: _CHRON_BASE["Earthshaker"],
  earthIn: tally.indexOf("Earthshaker") >= 0,
  shifter: _CHRON_BASE["Earth Shifter"],
  facetBases: %(facets)s.filter(function(n){ return _CHRON_BASE[n] !== "Jewel"; }),
  colInBase: col.filter(function(x){ return !!_CHRON_BASE[x.n]; }).map(function(x){ return x.n; })
}));
"""


class TheChronicleNamesEveryRow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _src()
        cls.block = _between(cls.src, BLOCK_START, BLOCK_END, "the chronicle name block")
        cls.pred = _between(cls.src, PRED_START, PRED_END, "the sunder predicate")
        with io.open(ROSTER, encoding="utf-8") as fh:
            cls.roster = json.load(fh).get("names") or []

    def drive(self):
        js = HARNESS % {
            "pred": self.pred,
            "block": self.block,
            "roster": json.dumps(self.roster),
            "facets": json.dumps(FACETS),
            "quests": json.dumps(QUESTS),
        }
        fd, path = tempfile.mkstemp(prefix=".chron_names_", suffix=".js", dir=HERE)
        try:
            with io.open(fd, "w", encoding="utf-8") as fh:
                fh.write(js)
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            self.skipTest("node unavailable - a skip is NOT a pass")
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        self.assertEqual(r.returncode, 0, "the name list threw:\n%s" % (r.stderr or "")[-1200:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_tally_is_the_game_file_count(self):
        o = self.drive()
        tally = o["tally"]
        print("   tally %d from roster %d" % (len(tally), len(self.roster)))
        self.assertEqual(len(tally), 397)
        self.assertEqual(len(set(tally)), 397)
        for n in FACETS:
            self.assertIn(n, tally)
        self.assertNotIn("Rainbow Facet", tally)
        self.assertNotIn("Polaris Spear", tally)
        self.assertNotIn("The Scourge", tally)
        for n in QUESTS:
            self.assertNotIn(n, tally)
        self.assertFalse(o["questSneaks"])
        self.assertEqual(o["questInBase"], [])
        for n in BARE_SUNDERS:
            self.assertIn(n, tally)
        self.assertEqual([n for n in tally if str(n).startswith("Latent ") or str(n).startswith("Renewed ")], [])
        for n in COLOSSAL:
            self.assertNotIn(n, tally)

    def test_colossal_jewels_are_their_own_six(self):
        o = self.drive()
        self.assertEqual(o["colossal"], COLOSSAL)
        self.assertEqual(o["colQ"], [110] * 6)

    def test_a_bare_facet_tick_matches_none_of_the_eight(self):
        o = self.drive()
        self.assertEqual(o["facetHits"], [])
        self.assertTrue(o["deathsWeb"])
        self.assertFalse(o["deathsFathom"])
        self.assertTrue(o["helm"])
        self.assertTrue(o["khalimKey"])

    def test_the_precrafted_index_aliases_onto_the_bare_sunder(self):
        o = self.drive()
        self.assertTrue(o["precraftAlias"])
        self.assertFalse(o["precraftIsUpgraded"])
        self.assertFalse(o["bareIsUpgraded"])

    def test_the_tick_writer_accepts_a_name_the_roster_does_not_carry(self):
        o = self.drive()
        self.assertTrue(o["tickFacet"])
        self.assertFalse(o["tickQuest"])
        self.assertTrue(o["tickCol"])
        self.assertFalse(o["tickBareFacet"])
        self.assertFalse(o["tickPolaris"])
        self.assertFalse(o["tickGull"])
        i = self.src.find("const _inUniRoster")
        j = self.src.find("const _gi", i)
        self.assertGreater(i, 0)
        self.assertGreater(j, i)
        body = self.src[i:j]
        self.assertEqual(body.count("_chronicleTickName(name)"), 1)

    def test_the_unidentified_line_is_the_base_and_earthshaker_stays(self):
        o = self.drive()
        self.assertEqual(o["baseMiss"], [])
        self.assertEqual(o["felloak"], "Club")
        self.assertEqual(o["gull"], "Dagger")
        self.assertEqual(o["blink"], "Leather Armor")
        self.assertEqual(o["broc"], "Leather Gloves")
        self.assertEqual(o["heavens"], "Mighty Scepter")
        self.assertEqual(o["redeemer"], "Mighty Scepter")
        self.assertEqual(o["tyrael"], "Sacred Armor")
        self.assertEqual(o["templar"], "Sacred Armor")
        self.assertEqual(o["storm"], "Scourge")
        self.assertEqual(o["horizon"], "Scourge")
        self.assertEqual(o["bane"], "Short Staff")
        self.assertEqual(o["web"], "Unearthed Wand")
        self.assertEqual(o["earth"], "Battle Hammer")
        self.assertTrue(o["earthIn"])
        self.assertEqual(o["shifter"], "Thunder Maul")
        self.assertEqual(o["facetBases"], [])
        self.assertEqual(o["colInBase"], [])
        self.assertNotIn("The Scourge", o["tally"])
        self.assertNotIn("Polaris Spear", o["tally"])

    def test_the_wall_and_the_search_read_that_base(self):
        self.assertEqual(self.src.count("function _tallyPool(isUni){"), 1)
        i = self.src.find("function _tallyPool(isUni){")
        j = self.src.find("window._tallySearchRun = function", i)
        self.assertGreater(j, i)
        pool = "\n".join(line.split("//", 1)[0] for line in self.src[i:j].split("\n"))
        chron = pool.find("if (typeof _CHRON_BASE !== 'undefined' && _CHRON_BASE[x.n]) base = _CHRON_BASE[x.n];")
        codex = pool.find("else base = (_codex && _codex[x.n] && _codex[x.n].base) || '';")
        self.assertGreater(chron, 0)
        self.assertGreater(codex, chron)
        self.assertIn("base: base", pool)
        k = self.src.find("window._tallySearchRun = function")
        m = self.src.find("window._tallySearchKey = function", k)
        self.assertGreater(m, k)
        run = "\n".join(line.split("//", 1)[0] for line in self.src[k:m].split("\n"))
        self.assertEqual(run.count("it.base != null && it.base !== ''"), 1)
        self.assertEqual(self.src.count('title="unidentified chronicle line"'), 1)
        self.assertEqual(self.src.count("var _missAll="), 1)
        w = self.src.find("var _missAll=")
        wall = self.src[w:self.src.find("v2769", w)]
        self.assertIn("_CHRON_BASE[x.n]", wall)
        self.assertIn("base:base", wall)

    def test_the_quest_gap_is_not_painted_as_dark(self):
        self.assertEqual(self.src.count("var _darkN=(s.chronTotal||0)-s.total;"), 1)
        self.assertEqual(self.src.count("var _showDark = _darkN;"), 1)
        self.assertNotIn("_darkN - _CHRON_QUESTS.length", self.src)
        self.assertNotIn("_CHRON_QUESTS.length", self.src)
        i = self.src.find("var _showDark = _darkN;")
        j = self.src.find("var _colRows", i)
        self.assertGreater(j, i)
        band = "\n".join(line.split("//", 1)[0] for line in self.src[i:j].split("\n"))
        self.assertIn("if(_showDark>0)", band)
        self.assertIn("'+_showDark+'", band)
        self.assertNotIn("'+_darkN+'", band)
        self.assertEqual(self.src.count("s.chronTotal-s.found"), 1)
        self.assertEqual(self.src.count("_colossalStillOpen("), 3)
        self.assertIn("_ownedHas(_ownF, x.n)", self.src)
        self.assertNotIn("_ownF.has(x.n)", self.src)
        self.assertIn("(s.chronTotal || 0) - s.found + _colossalStillOpen(", self.src)
        self.assertNotIn("s.chronTotal-s.found-_CHRON_QUESTS.length", self.src)
        k = self.src.find("var _namedDark = (s.chronTotal - s.total);")
        self.assertGreater(k, 0)
        m = self.src.find("H.push(_undoBar('uni'))", k)
        self.assertGreater(m, k)
        note = "\n".join(line.split("//", 1)[0] for line in self.src[k:m].split("\n"))
        self.assertNotIn("quest items sit inside the ", note)
        self.assertIn("every chronicle row is named", note)
        fn = self.src[self.src.find("window.d2rChronTotal = function"):self.src.find("window._publishedLane")]
        self.assertNotIn("_CHRON_QUESTS", fn)
        self.assertNotIn("return t - q", fn)
        self.assertIn("return t;", fn)
        flat = self.src.replace(" ", "")
        self.assertIn("chronTotal:397", flat)
        self.assertNotIn("chronTotal:403", flat)

    def test_the_list_is_actually_called_and_the_resolver_stops(self):
        self.assertEqual(self.src.count("names = _chronicleNameList(names);"), 1)
        i = self.src.find("function _ownedHas(own, n){")
        j = self.src.find("function _diffRank", i)
        self.assertGreater(i, 0)
        self.assertGreater(j, i)
        body = self.src[i:j]
        hit = body.find("_chronicleIndexHit(own, n)")
        stop = body.find("_chronicleStopResolver(n)")
        resolve = body.find("d2rResolveItem")
        self.assertGreater(hit, 0)
        self.assertGreater(stop, hit)
        self.assertGreater(resolve, stop)


if __name__ == "__main__":
    unittest.main(verbosity=2)
