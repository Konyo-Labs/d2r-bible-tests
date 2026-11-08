# -*- coding: utf-8 -*-
"""#85 - QUICK WINS RANKS EVERY PLACE AN EARLY UNIQUE DROPS, BY FEWEST RUNS, ON SILOSPEN'S OWN NUMBERS.

His ask 2026-11-06 (Uniques > Quick wins, Bane Ash): the console said "Run Normal Andariel ~3.6h" while silospen's
calculator - the source of every stored 1:N on the page - ranks Coldcrow in Cave Level 1 first and the Cow King second.
MEASURED before the change: the page's boss odds ARE silospen's (Bane Ash from Normal Andariel 1:2,538 stored, 1:2,539
there; the Countess 1:7,800 / 1:7,801; Mephisto 1:7,739 both). The gap was the CANDIDATE LIST - bosses only. So:

  1. QW_PLACES is silospen's per-item answer (tv/silospen_places.py, read-only): every boss and super-unique that drops
     an early unique, MF 300 /players 1 like BOSSES. A place the page already runs keeps its stored figure - and that
     figure is held here to silospen's (test_a_place_the_page_already_runs_keeps_silospens_figure).
  2. Every NEW place carries its own /players factor (PLACE_PF), read on silospen p(P)/p(1): a super-unique's treasure
     class is its own - Coldcrow does not move at any /players, Blood Raven moves x1.46, a Defiler x2.29. playerMult is
     still the one /players path (test_one_players_path).
  3. The page's arithmetic is held to silospen's printed figure at MF 0 / 300 / 700 / 1000 and /players 1-8 for every
     new place it keeps - on the item each factor was read from AND on every other item that carries the place, so the
     factor is tested where it was not measured.
  4. _qwPlaces ranks by RUNS to an even chance (hoursFor at one run an hour - the same clock as the hours); the hours sit
     beside them. The Cow King (his kill bars that character from the cow level in that difficulty) and RANDOM packs (a
     unique or champion that spawns by chance - silospen prices a kill, nobody can price a run) are shown by _qwAlso and
     never ranked as a run.
The page's own code runs in node (cut from bible.html: BOSSES, the registry build, the drop engine, the forge's odds seam
and the ranker); every expectation is recomputed from the vendored readings, never typed. RED_PROOF below.
[[unknown-stays-unknown]] [[the-unjoined-end]]
"""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from console_safe import enable  # noqa: E402
enable()

ROOT = os.path.dirname(HERE)
BIBLE = os.path.join(ROOT, "bible.html")
DATA = os.path.join(HERE, "data", "silospen_places_rotw30.json")
NODE = shutil.which("node")
EPS = 0.00025                 # the reach the eleven boss farms' factors measured (REG-2953): every /players check is held to it
MF_EPS = 0.0025               # REG-3244: an MF check may miss by the game's SECOND integer division, chance x 100 / (100 +
                              # effective MF) on the item's own quality numbers, which the page does not carry - measured worst
                              # 0.24% (Felloak from Normal Coldcrow at MF 0, 1:831 against 1:829), 3 of 451 checkpoints
MF_STRICT_SHARE = 0.96        # and at least this share of MF checks sit inside EPS, so the wider bound cannot hide a regression
# REG-3290 (v3876, every unique pulled): 0.97 was measured on the 148 early uniques (3 of 451 outside EPS). With all 388 and
# 44 new super-unique targets the checkpoints carry many more MF 700/1000 kills: 47 of 1539 sit outside EPS (96.95%) - 15 of
# 474 at qlvl<=35, 3 of 387 at 36-60, 29 of 678 above 60 - the worst 0.044% bar the known Felloak MF 0 (0.24%), and none
# outside MF_EPS. A roll that drifted would move far more than 4%; the floor still catches that.
ROUNDING = 0.5e-11            # silospen prints 11 decimals
NOT_THE_SAME_RUN = {"travincal"}     # the page's council run sums three kills; silospen prices one member at a time


def _read():
    with open(BIBLE, encoding="utf-8") as fh:
        return fh.read()


def _data():
    with open(DATA, encoding="utf-8") as fh:
        return json.load(fh)


def _cut(src, start, end):
    if src.count(start) != 1:
        raise AssertionError("cut start %r occurs %d times - re-point this law" % (start[:60], src.count(start)))
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


def _code(src):
    """bible.html with its comments removed (bounded block comments, then line comments)."""
    src = re.sub(r"/\*.{0,4000}?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(^|[^:\\'\"])//[^\n]*", r"\1", src)


def _table(src, name):
    m = re.search(r"\nconst %s = (\{.*?\});\n" % re.escape(name), src)
    if not m:
        raise AssertionError("the page carries no %s table" % name)
    return json.loads(m.group(1))


def _bosses(src):
    line = next(ln for ln in src.split("\n") if ln.startswith("const BOSSES = "))
    body = line[len("const BOSSES = "):]
    return {b["id"]: b for b in json.loads(body[:body.rindex("];") + 1])}


def _round(x):
    return int(math.floor(x + 0.5))


def _near(got, want, ps=(), eps=EPS):
    slack = want * (eps + sum(ROUNDING / p for p in ps))
    return got is not None and abs(got - want) <= max(1, int(math.ceil(slack)))


def _node(prog):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


SCENARIO = r"""
var out = { eff: [], rank: {}, also: {} };
CASES.forEach(function(c){ mf = c[3]; players = c[4]; out.eff.push(effChance(c[2], c[0], c[1])); });
RANK.forEach(function(r){
  mf = r[1]; players = r[2];
  var it = ITEM_REGISTRY[r[0]] || { n: r[0], sources: [] };
  var q = _qwPlaces({ n: r[0], sources: it.sources });
  out.rank[r.join('|')] = q.map(function(p){ return [p.label, p.runs, p.hours, p.s.bossId, p.est]; });
  out.also[r.join('|')] = _qwAlso({ n: r[0] }, _qwWorst(q)).map(function(a){ return [a.who, a.kind, a.chance]; });
});
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to drive the page's own drop math")
class QuickWinsRanksEveryPlace(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        cls.data = _data()
        cls.bosses = _bosses(cls.src)
        cls.targets = _table(cls.src, "QW_TARGETS")
        cls.places = _table(cls.src, "QW_PLACES")
        cls.pf = _table(cls.src, "PLACE_PF")
        cls.cases, cls.want = [], []
        base = {}
        for nm, tid, d, mf, P, p, _src in cls.data["checks"]:
            if mf == 300 and P == 1:
                base[(nm, tid, d)] = max(1, _round(1.0 / p))      # the base the page stores for a place: 1:N at MF 300 /p1
        for nm, tid, d, mf, P, p, src_item in cls.data["checks"]:
            b = base.get((nm, tid, d))
            cls.cases.append([tid, d, b, mf, P])
            cls.want.append(((nm, tid, d, mf, P, src_item), _round(1.0 / p), (p,)))
        cls.rank_keys = []
        for nm in sorted(cls.places):
            for mf, P in ((0, 1), (300, 1), (300, 8), (699, 3), (1000, 1)):
                cls.rank_keys.append([nm, mf, P])
        bl = next(ln for ln in cls.src.split("\n") if ln.startswith("const BOSSES = "))
        registry = _cut(cls.src, "const ITEM_REGISTRY = {};", "window.ITEM_REGISTRY = ITEM_REGISTRY;")
        engine = _cut(cls.src, "const effMF = (gMF, factor) =>", "// GRAIL-FARM BRIDGE")
        seam = _cut(cls.src, "  var _MFB_BASE = {", "  window._fAdjC = _adjC;")
        ranker = _cut(cls.src, "  var _QW_DIFF = ", "  function _qwRunsTxt(n){")
        prelude = ("var window = {}; var document = { getElementById: function(){ return null; } };\n"
                   "var ITEMS = []; var mf = 300, players = 1;\nvar CASES = %s;\nvar RANK = %s;\n"
                   % (json.dumps(cls.cases), json.dumps(cls.rank_keys)))
        cls.o = _node(prelude + bl.replace("const BOSSES", "var BOSSES", 1) + "\n" + registry + "\n" + engine + "\n"
                      + seam + "\n" + ranker + "\n" + SCENARIO)

    def test_the_pull_is_the_source_the_page_stores(self):
        d = self.data
        for part in ("version=D2R_ROW_3_0", "party=1", "desecrated=false", "itemQuality=UNIQUE"):
            self.assertIn(part, d["query"], "the pull is not the one the stored 1:N came from: %s" % part)
        self.assertEqual(d["baseMf"], 300, "the stored bases are silospen's at MF 300")
        self.assertGreater(len(self.places), 50, "premise: the page carries the early uniques' places")

    def test_every_new_place_names_its_own_players_factor(self):
        bad = []
        for nm, v in sorted(self.places.items()):
            for tid, d, n in v["f"]:
                if tid in self.bosses:
                    continue
                if tid not in self.targets:
                    bad.append("%s: %s is neither a run the page has nor a new target" % (nm, tid))
                elif len((self.pf.get(tid) or {}).get(d) or []) != 8:
                    bad.append("%s: %s %s has no /players factor of its own" % (nm, tid, d))
        self.assertEqual(bad, [], "\n  ".join(bad[:20]))

    def test_a_place_the_page_already_runs_keeps_silospens_figure(self):
        """#85 (1), his question: is the page's per-item drop math the calculator's? For every early unique a run the
        page already has drops, the stored 1:N is silospen's at MF 300 /players 1."""
        checked, bad = 0, []
        for nm, v in sorted(self.places.items()):
            for tid, d, n in v["f"]:
                if tid not in self.bosses or tid in NOT_THE_SAME_RUN:
                    continue
                row = next((r for r in self.bosses[tid]["dropTable"] if r["n"] == nm), None)
                if row is None or row.get(d) in (None, 0):
                    continue
                checked += 1
                if not _near(row[d], n, ()):
                    bad.append("%s from %s %s: page 1:%s, silospen 1:%s" % (nm, d, tid, row[d], n))
        self.assertGreater(checked, 100, "premise: too few stored figures were compared to mean anything (%d)" % checked)
        self.assertEqual(bad, [], "%d of %d stored figures are not silospen's:\n  %s" % (len(bad), checked, "\n  ".join(bad[:20])))

    def test_a_stored_figure_silospen_never_gives_is_refused(self):
        """v3884 (REG-3439, GrokBot 6720166936 + the boss audit 11-08: Tyrael's Might stored Hell Diablo 1:29,750 - silospen has
        no plain Hell Diablo row for it at any MF, its best boss is Hell Baal 1:186,145). The case above only checks stored
        figures silospen ALSO gives. The pull keeps each item's best KEEP_FIXED fixed places, so a stored boss figure better
        than the worst kept one would have been kept: absent, silospen never gives it."""
        import silospen_places as SP
        checked, bad = 0, []
        for nm, v in sorted(self.places.items()):
            kept = dict(((tid, d), n) for tid, d, n in v["f"])
            if not kept:
                continue
            worst = max(kept.values())
            complete = len(kept) < SP.KEEP_FIXED
            for tid, b in sorted(self.bosses.items()):
                if tid in NOT_THE_SAME_RUN or tid in ("pit", "cows"):    # areas: per-kill tables, never a fixed place
                    continue
                row = next((r for r in b["dropTable"] if r["n"] == nm), None)
                for d in ("norm", "nm", "hell"):
                    st = row.get(d) if row else None
                    if st in (None, 0) or (tid, d) in kept:
                        continue
                    checked += 1
                    if complete or st < worst:
                        bad.append("%s from %s %s: page 1:%s - silospen keeps %d place(s), worst 1:%s, and not this one"
                                   % (nm, d, tid, st, len(kept), worst))
        self.assertGreater(checked, 100, "premise: too few stored figures outside silospen's kept places (%d)" % checked)
        self.assertEqual(bad, [], "%d stored figure(s) silospen never gives:\n  %s" % (len(bad), "\n  ".join(bad[:20])))

    def test_each_new_place_moves_with_mf_and_players_as_silospen_does(self):
        got = self.o["eff"]
        self.assertEqual(len(got), len(self.want), "premise: every case came back")
        bad, indep, mf_n, mf_strict = [], 0, 0, 0
        for g, ((nm, tid, d, mf, P, src_item), want, ps) in zip(got, self.want):
            indep += 0 if src_item else 1
            if mf != 300:
                mf_n += 1
                mf_strict += 1 if _near(g, want, ps) else 0
            if not _near(g, want, ps, eps=MF_EPS if mf != 300 else EPS):
                bad.append("%s from %s %s at MF %d /players %d: page 1:%s, silospen 1:%s" % (nm, d, tid, mf, P, g, want))
        self.assertGreater(len(got), 0, "premise: the evidence carries no checkpoint")
        self.assertGreater(indep, 0, "every check is on the item its own factor was read from - nothing independent")
        self.assertEqual(bad, [], "%d of %d checkpoints miss silospen:\n  %s" % (len(bad), len(got), "\n  ".join(bad[:25])))
        self.assertGreater(mf_n, 50, "premise: too few MF checkpoints (%d)" % mf_n)
        self.assertGreaterEqual(mf_strict, MF_STRICT_SHARE * mf_n,
                                "only %d of %d MF checkpoints sit inside %.3f%% - the MF roll drifted off silospen's"
                                % (mf_strict, mf_n, EPS * 100))

    def test_bane_ash_ranks_as_he_read_it_on_silospen(self):
        """His example: silospen ranks Coldcrow (Cave Level 1) first. The Cow King and the random packs he read are on
        the card as per-kill readings, never as a counted run."""
        k = "Bane Ash|300|1"
        rank, also = self.o["rank"].get(k) or [], self.o["also"].get(k) or []
        self.assertTrue(rank, "Bane Ash has no ranked place")
        self.assertEqual(rank[0][0], "Normal Coldcrow", "Bane Ash's 1st place: %s" % [r[0] for r in rank[:4]])
        self.assertNotIn("Normal The Cow King", [r[0] for r in rank], "the Cow King is ranked as a run he can repeat")
        whos = [a[0] for a in also]
        self.assertIn("Normal The Cow King", whos, "the Cow King's per-kill reading is not on the card: %s" % whos)
        self.assertIn("Normal The Banished", whos, "the random pack he read is not on the card: %s" % whos)

    def test_every_list_is_ranked_by_runs_and_ranks_only_runs(self):
        once = set(t for t, v in self.targets.items() if v.get("once"))
        rnd = set()
        for v in self.places.values():
            for r in v.get("r") or []:
                rnd.add(r[0])
        rnd -= set(t["n"] for t in self.targets.values())      # a pack's name that is also a target's is the target
        bad = []
        for key, rows in sorted(self.o["rank"].items()):
            runs = [r[1] for r in rows]
            if any(x is None for x in runs) or runs != sorted(runs):
                bad.append("%s: not in runs order %s" % (key, [(r[0], r[1]) for r in rows[:6]]))
            for r in rows:
                if r[3] in once:
                    bad.append("%s: ranks %s, whose kill is not a repeatable run" % (key, r[0]))
                if r[0].split(" ", 1)[-1] in rnd:
                    bad.append("%s: ranks the random pack %s" % (key, r[0]))
        self.assertGreater(len(self.o["rank"]), 100, "premise: too few lists were ranked")
        self.assertEqual(bad, [], "\n  ".join(bad[:20]))

    def test_one_players_path(self):
        code = _code(self.src)
        pm = _cut(code, "function playerMult(bossId, diffKey, players){", "\n    }\n")
        self.assertIn("PLACE_PF[", pm, "playerMult does not read the new places' own factors")
        self.assertEqual(code.count("\nconst PLACE_PF = "), 1, "premise: one definition of the new places' factor table")
        rest = code.replace(pm, "").replace("\nconst PLACE_PF = ", "\n")
        self.assertNotIn("PLACE_PF", rest, "the new places' factor table is read outside playerMult - a second /players path")


RED_PROOF = [
    {'why': "v3884 (REG-3439) - Tyrael's Might's Hell Diablo row comes back (silospen never gives it)",
     'file': 'bible.html',
     'find': '{"n":"Templar\'s Might","tc":87,"qlvl":82,"tier":"grail","norm":null,"normTz":null,"nm":null,"nmTz":null,"hell":null,"hellTz":2622},{"n":"Tyrael\'s Might","tc":87,"qlvl":87,"tier":"uber","norm":null,"normTz":null,"nm":null,"nmTz":null,"hell":null,"hellTz":20975}',
     'replace': '{"n":"Templar\'s Might","tc":87,"qlvl":82,"tier":"grail","norm":null,"normTz":null,"nm":null,"nmTz":null,"hell":null,"hellTz":2622},{"n":"Tyrael\'s Might","tc":87,"qlvl":87,"tier":"uber","norm":null,"normTz":null,"nm":null,"nmTz":null,"hell":29750,"hellTz":20975}',
     'matches': 1},
    {'why': "REG-3302 - Nihlathak's nightmare Opalvein figure goes back to the v41 number silospen does not give",
     'file': 'bible.html',
     'find': '{"n":"Opalvein","tc":0,"qlvl":58,"tier":"grail","nc":1,"norm":18642,"normTz":19800,"nm":20055,',
     'replace': '{"n":"Opalvein","tc":0,"qlvl":58,"tier":"grail","nc":1,"norm":18642,"normTz":19800,"nm":20976,',
     'matches': 1},
    {"why": "REG-3244 - the quality roll keeps the fraction of effective MF the game truncates: 94 of 123 MF checks miss",
     "file": "bible.html",
     "find": "  const refEff = Math.floor(effMF(300, 250));\n  const userEff = Math.floor(effMF(gMF, 250));\n",
     "replace": "  const refEff = effMF(300, 250);\n  const userEff = effMF(gMF, 250);\n",
     "matches": 1},
    {"why": "#85 - playerMult forgets the new places' own factors: Blood Raven, the Summoner and the Defilers stop moving "
            "with /players",
     "file": "bible.html",
     "find": "      var f = (PLAYER_F[bossId] || (typeof PLACE_PF !== 'undefined' && PLACE_PF[bossId]) || {})[tier];   // #85 - a new place's own measured factor\n",
     "replace": "      var f = (PLAYER_F[bossId] || {})[tier];\n",
     "matches": 1},
    {"why": "#85 - the Cow King is ranked as a run (his kill bars the character from the cow level in that difficulty)",
     "file": "bible.html",
     "find": "        if (!T || T.once || seen[tid + '|' + dk]) return;\n",
     "replace": "        if (!T || seen[tid + '|' + dk]) return;\n",
     "matches": 1},
    {"why": "#85 - the places are ranked by hours (an estimated run rate) instead of runs",
     "file": "bible.html",
     "find": "    return out.sort(function(a, b){ return (a.runs - b.runs) || (_qwH(a) - _qwH(b)) || (a.label < b.label ? -1 : a.label > b.label ? 1 : 0); });\n",
     "replace": "    return out.sort(function(a, b){ return (_qwH(a) - _qwH(b)) || (a.runs - b.runs) || (a.label < b.label ? -1 : a.label > b.label ? 1 : 0); });\n",
     "matches": 1},
    {"why": "#85 - bosses only again: the silospen places are never candidates (Bane Ash goes back to Andariel)",
     "file": "bible.html",
     "find": "      ((P && P.f) || []).forEach(function(r){\n        var tid = r[0], dk = r[1], n = r[2], T =",
     "replace": "      ([]).forEach(function(r){\n        var tid = r[0], dk = r[1], n = r[2], T =",
     "matches": 1},
]


if __name__ == "__main__":
    unittest.main()
