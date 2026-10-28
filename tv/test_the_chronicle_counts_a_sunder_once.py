#!/usr/bin/env python3
"""THE CHRONICLE COUNTS A SUNDER ONCE — and the roster still knows every form.

HIS RULING, first on 2026-09-05 and again on 2026-09-15 when it came up in the vault:

    v2680  *"yes we have latent of bone break but the chronicle itself is not latent thats just
            the upgraded version of it after we upgrade in hordaic cube.. so for the chronicle
            all sunders 6 of them need to be counted in the chronicle specifically as 1 tally for
            each.. and for the vault that a different story the entire item database should be
            there regardless."*

    v3183  *"each its own.. for chronicle there is only one name for it.. and for items found or
            stashed or items renewed from the hordaic cube these are their own entity in vault
            terms"*

⚠⚠ THIS LAW EXISTS BECAUSE THE RULING HAS ALREADY BEEN IMPLEMENTED, BROKEN, AND REBUILT.

    v2680  honoured it by filtering the six `Latent <sunder>` names out of the ROSTER.
    v2685  reverted that, because the roster is not the chronicle's tally — it is the resolution
           table for the whole board, and removing a name removes the item's CARD, its FARM ROUTE
           and its ART. It also contradicted his earlier v1720 ruling ("add the 11 rotw items to
           the roster"); the Latent charms are among those eleven. 8 CI failures, all self-
           inflicted. The revert recorded the correct diagnosis: *"he wants the item findable and
           openable (roster) AND counted once (chronicle tally). Those are two different surfaces
           and the fix belongs on the tally, not here."*
    v2691  put it on the tally, where it lives now: `_uniItems()` drops upgraded spellings from
           the CHRONICLE universe while `_gUniqueRoster()` keeps all of them.

Nothing gated any of it. A ruling that has already swung twice, with a correct fix and an
incorrect fix that differ by WHICH SURFACE they touch, is exactly the shape that regresses a
third time. So this law pins BOTH halves, because either one alone is the bug:

    FOLDED in the tally   — or he is asked to find the same charm twice
    PRESENT in the roster — or the charm loses its card, its art and its farm route

MEASURED at the time of writing: roster 398 names including 6 `Latent …`; funiScan().total 392.
398 − 6 = 392, and the six BARE sunders survive. The file count was 403 rows, with six
sunder rows and zero Latent rows. The pin is the chronicle number, 397, and this law does not move it.

⚠ ON READING THE SOURCE. The predicate and the fold are extracted with BOTH ends anchored and
executed in node, so this law tests the SHIPPED behaviour rather than the presence of words that
describe it. A fixed-size window past a region reads as ABSENT and would let this pass on a file
that no longer contains the fold. [[source-reading-guard]]
"""
import io
import json
import os
import re
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

PRED_START = "  var _CHRON_SUNDER_BASES = ["
PRED_END = "  window._isUpgradedSunder = _isUpgradedSunder;"
FOLD_START = "    names = (function(_n){"
FOLD_END = "    })(names);"


def _src():
    with io.open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _between(src, start, end, what):
    i = src.find(start)
    assert i >= 0, "%s: the opening anchor is gone from bible.html" % what
    j = src.find(end, i)
    assert j > i, "%s: the closing anchor is gone from bible.html" % what
    return src[i:j + len(end)]


HARNESS = """
// the extracted block publishes onto `window`, which node has not got. Defining it here rather
// than editing the extraction keeps this law driving the SHIPPED bytes verbatim.
var window = {};

%(pred)s

var names = %(roster)s;
%(fold)s
var kept = names;

var objIn = {};
%(roster)s.forEach(function(n, i){ objIn['k'+i] = n; });
names = objIn;
%(fold)s
var keptObj = Object.keys(names).map(function(k){ return names[k]; });

console.log(JSON.stringify({
  bases: _CHRON_SUNDER_BASES,
  predicate: {
    latent:  _CHRON_SUNDER_BASES.map(function(b){ return _isUpgradedSunder('Latent ' + b); }),
    renewed: _CHRON_SUNDER_BASES.map(function(b){ return _isUpgradedSunder('Renewed ' + b); }),
    bare:    _CHRON_SUNDER_BASES.map(function(b){ return _isUpgradedSunder(b); })
  },
  keptArray: kept,
  keptObject: keptObj
}));
"""


class TheChronicleCountsASunderOnce(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        src = _src()
        cls.pred = _between(src, PRED_START, PRED_END, "the sunder predicate")
        cls.fold = _between(src, FOLD_START, FOLD_END, "the chronicle fold")
        with io.open(ROSTER, encoding="utf-8") as fh:
            cls.roster = (json.load(fh).get("names") or [])

    def drive(self, roster=None):
        js = HARNESS % {"pred": self.pred, "fold": self.fold,
                        "roster": json.dumps(roster if roster is not None else self.roster)}
        fd, p = tempfile.mkstemp(prefix=".sunder_drive_", suffix=".js", dir=HERE)
        try:
            with io.open(fd, "w", encoding="utf-8") as fh:
                fh.write(js)
            r = subprocess.run(["node", p], capture_output=True, text=True, timeout=60)
        except FileNotFoundError:   # REG-1900 - the ONE skip: no node here. A timeout is the subject's failure
            self.skipTest("node unavailable - a skip is NOT a pass")
        finally:
            try:
                os.unlink(p)
            except OSError:
                pass
        self.assertEqual(r.returncode, 0,
                         "the shipped sunder fold threw:\\n%s" % (r.stderr or "")[-900:])
        return json.loads(r.stdout.strip().splitlines()[-1])

    # ── the six ────────────────────────────────────────────────────────────────────────────
    def test_there_are_exactly_six_sunders(self):
        o = self.drive()
        print("   sunder bases: %r" % (o["bases"],))
        self.assertEqual(len(o["bases"]), 6,
                         "the game's Chronicle carries exactly six sunder rows")
        self.assertEqual(sorted(o["bases"]),
                         sorted(["Bone Break", "Cold Rupture", "Crack of the Heavens",
                                 "Flame Rift", "Rotting Fissure", "Black Cleft"]))

    def test_both_upgraded_spellings_are_recognised(self):
        """Latent is what drops; Renewed is what the Horadric Cube makes. Both are the same
        chronicle line as the bare name."""
        o = self.drive()
        print("   latent=%r renewed=%r bare=%r"
              % (o["predicate"]["latent"], o["predicate"]["renewed"], o["predicate"]["bare"]))
        # REG-1893 - the three lists map _CHRON_SUNDER_BASES; an emptied list passes all() and any() alike.
        self.assertTrue(o["bases"] and o["predicate"]["latent"],
                        "no sunder base was driven, so 'every spelling is recognised' would judge none: %r"
                        % (o["bases"],))
        self.assertTrue(all(o["predicate"]["latent"]), "a Latent spelling was not recognised")
        self.assertTrue(all(o["predicate"]["renewed"]), "a Renewed spelling was not recognised")
        self.assertFalse(any(o["predicate"]["bare"]),
                         "a BARE sunder was treated as an upgraded form - the chronicle would "
                         "then count that charm ZERO times, not once")

    # ── half one: FOLDED in the tally ──────────────────────────────────────────────────────
    def test_the_chronicle_universe_holds_one_row_per_sunder(self):
        o = self.drive()
        for key in ("keptArray", "keptObject"):
            kept = o[key]
            # ⚠ A DOUBLED BACKSLASH HERE MATCHED NOTHING AND THE TEST COULD NOT FAIL. Written
            # as r"...\\s" the pattern asks for a literal backslash, so `up` was ALWAYS empty
            # and this assertion passed over a deleted fold. Caught only because the sabotage
            # that deletes the fold came back GREEN - the sabotage was right and the law was
            # broken. [[sabotage-is-usually-the-wrong-one]]
            up = [n for n in kept if re.match(r"^(Latent|Renewed) ", str(n))]
            self.assertTrue(o["bases"], "the fixture lost its own base list")
            bare = [b for b in o["bases"] if b in kept]
            print("   %-10s kept=%d upgraded-left=%d bare-present=%d"
                  % (key, len(kept), len(up), len(bare)))
            self.assertEqual(up, [],
                             "%s: an upgraded sunder survived into the chronicle universe - he "
                             "is being asked to find the same charm twice" % key)
            self.assertEqual(len(bare), 6,
                             "%s: a bare sunder was dropped too, so the chronicle counts it "
                             "ZERO times" % key)

    def test_the_object_branch_is_the_one_that_actually_runs(self):
        """_gUniqueRoster() returns an OBJECT (norm -> canonical). An array-only fold would look
        correct in review and do nothing in production — the v2680 cut failed exactly this way,
        matching nothing while looking right."""
        o = self.drive()
        self.assertEqual(len(o["keptObject"]), len(self.roster) - 6,
                         "the object branch of the fold did not drop the six upgraded forms")

    def test_the_arithmetic_is_the_one_he_reads(self):
        o = self.drive()
        print("   roster %d - 6 upgraded = %d kept" % (len(self.roster), len(o["keptArray"])))
        self.assertEqual(len(o["keptArray"]), len(self.roster) - 6)

    # ── half two: PRESENT in the roster (the half v2680 broke) ─────────────────────────────
    def test_the_roster_still_carries_every_form(self):
        """⚠ THE REGRESSION THIS LAW EXISTS FOR. Removing these from the roster is what v2680
        shipped: the charms lost their cards, their art and their farm routes, and it contradicted
        his v1720 ruling that the eleven RotW items belong in the roster. The fold must live on
        the TALLY and nowhere else."""
        latent = [n for n in self.roster if str(n).startswith("Latent ")]
        print("   roster carries %d Latent form(s) of %d names" % (len(latent), len(self.roster)))
        self.assertEqual(len(latent), 6,
                         "the Latent sunders were removed from the ROSTER - that is the v2680 "
                         "regression: the item stops being openable, loses its art and its farm "
                         "route. Fold the TALLY, never the roster")
        for b in ("Bone Break", "Cold Rupture", "Crack of the Heavens",
                  "Flame Rift", "Rotting Fissure", "Black Cleft"):
            self.assertIn(b, self.roster, "the bare sunder %r left the roster" % b)

    def test_the_vault_still_treats_the_forms_as_separate_entities(self):
        """The other half of his ruling, and the reason the roster must keep them: the vault is
        an inventory, not a checklist. [[item_identity]]"""
        import item_identity as ii
        keys = [ii.vault_key(n) for n in
                ("Black Cleft", "Latent Black Cleft", "Renewed Black Cleft")]
        print("   vault keys: %r" % (keys,))
        self.assertEqual(len(set(k.lower() for k in keys)), 3,
                         "the vault folded the sunder forms - the chronicle counts once, the "
                         "vault counts things, and they are not the same question")
        self.assertEqual(len(set(ii.chronicle_key(n).lower() for n in
                                 ("Black Cleft", "Latent Black Cleft", "Renewed Black Cleft"))), 1,
                         "the chronicle key must be one name for all three forms")

RED_PROOF = [
    {"why": "a Renewed sunder from the Horadric Cube is not recognised, so the chronicle asks for the same charm twice",
     "file": "bible.html",
     "find": "      if (s === 'Latent ' + b || s === 'Renewed ' + b) return true;\n",
     "replace": "      if (s === 'Latent ' + b) return true;\n",
     "matches": 1, "needs": "node"},
    {"why": "a BARE sunder is treated as an upgraded form, so the chronicle counts that charm zero times",
     "file": "bible.html",
     "find": "      if (s === 'Latent ' + b || s === 'Renewed ' + b) return true;\n",
     "replace": "      if (s === 'Latent ' + b || s === 'Renewed ' + b || s === b) return true;\n",
     "matches": 1, "needs": "node"},
    {"why": "v2680's shape - the fold's OBJECT branch, the one _gUniqueRoster() actually feeds, drops nothing",
     "file": "bible.html",
     "find": "        Object.keys(_n).forEach(function(k){ if (!_isUpgradedSunder(_n[k])) _o[k] = _n[k]; });\n",
     "replace": "        Object.keys(_n).forEach(function(k){ _o[k] = _n[k]; });\n",
     "matches": 1, "needs": "node"},
    {"why": "the array branch of the chronicle fold keeps the upgraded spellings",
     "file": "bible.html",
     "find": "          return _n.filter(function(x){ return !_isUpgradedSunder(x); });\n",
     "replace": "          return _n;\n",
     "matches": 1, "needs": "node"},
    {"why": "the sunder base list drops one of the game's six Chronicle sunder rows",
     "file": "bible.html",
     "find": "'Flame Rift','Rotting Fissure','Black Cleft'];",
     "replace": "'Flame Rift','Rotting Fissure'];",
     "matches": 1, "needs": "node"},
    {"why": "v2680 - a Latent sunder is removed from the ROSTER, so the charm loses its card, its art and its farm route",
     "file": "tv/unique_roster.json",
     "find": "  \"Latent Bone Break\",\n",
     "replace": "",
     "matches": 1},
    {"why": "the vault folds the sunder forms into one entity, though it counts things rather than grail lines",
     "file": "tv/item_identity.py",
     "find": "    return (\"%s %s\" % (qual, core)).strip() if qual else core\n",
     "replace": "    return core\n",
     "matches": 1},
    {"why": "the chronicle key keeps the qualifier, so Latent and Renewed answer separate grail lines",
     "file": "tv/item_identity.py",
     "find": "    _qual, core = split_name(name)\n    return core\n",
     "replace": "    _qual, core = split_name(name)\n    return name\n",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main(verbosity=2)
