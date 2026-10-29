# -*- coding: utf-8 -*-
"""REG-2953 - /PLAYERS MOVES EVERY 1:N BY SILOSPEN'S OWN FACTOR: IT STEPS WHERE THE GAME STEPS, BY THE SIZE THE GAME GIVES.

REG-2509 (OPEN since v3791): effChance divided every 1:N by a one-NoDrop model, (1 - q^k)/(1 - q) with
k = 1 + floor(players / 2) and one q per boss (PLAYER_Q). His instruction on the task: re-measure against silospen
RotW 3.0 before changing anything. Pulled read-only from silospen's own calculator (the source of every stored 1:N):
D2R_ROW_3_0, party 1, MF 300, the 11 farms the page scales x Normal / Nightmare / Hell, every unique (/players 1-8) and
every set item (/players 1, 3, 5, 7). tv/data/silospen_players_rotw30.json keeps the items this law reads - per cell and
quality the most common and the rarest item, the lowest and the highest p(7)/p(1), and named ones - with their raw
probabilities, and the measured reach of the whole table.
  * THE STEPS. silospen pairs /players 1=2, 3=4, 5=6, 7=8 on every farm and difficulty but one (Hell Duriel gains 1.4%
    at /p2). That is the pairing the page had before 0e22e7d2 (2026-06-01) moved it to 2=3, 4=5, 6=7 and wrote "verified
    vs silospen" in its message - so the page showed a gain at /p2 the game does not give, and stepped one late after.
    The Prime Evils stop gaining at /p5.
  * THE SIZE. One top-level NoDrop cannot reach it: Andariel moves x1.79 at /p8 where the model capped at x1.39, and
    Countess and Duriel - held at x1.00 and tagged P#-PROOF - move x1.39 and x1.37. Pindleskin is the one farm whose
    table does not move at any /players, so he keeps the tag.
  * THE SPREAD decided the shape. Within one farm and difficulty the per-item factor p(P)/p(1) varies only with how
    common the item is (several picks saturate a common item), so one factor per farm, difficulty and /players
    (PLAYER_F, the rare-item factor) reproduces silospen's 1:N over the WHOLE pull - 60,679 item x /players cells -
    within one count or 0.023% of N, whichever is larger. EPS below is that measured reach, rounded up.
  * REG-2955 - THE TERROR ZONES. A terror-zone column (normTz / nmTz / hellTz) has its own factor, pulled the same way
    (desecrated, at the levels the stored TZ columns were read at: 50 / 76 / 99). It is not its difficulty's: Andariel's
    Hell zone moves x1.753 at /p8 against x1.792 and gains 0.8% at /p2 on Nightmare and Hell; Hell Duriel's zone has no
    /p2 step. silospen prints 11 decimals, so a 1:150,000,000 item carries 3 significant digits: ROUNDING is that.
  * REG-2954 - THE PIT IS PIT LEVEL 1 (his ruling). Its dweller is a melee one (fallen3, the Devilkin): levels.txt
    gives Pit Level 1 skeleton3, fallen3, corruptrogue3 and cr_archer3, and the archer alone rolls the Miss table
    (Equip 13 of 160 against H2H's 16 of 160) - the "13/16" the first pull of the archer showed. The stored Nightmare
    column was Pit Level 2's; it is Pit Level 1's now. BASE_NOT_THIS_PULL is empty and refuses a farm that drifts.
  * #190 Q7 (his ruling) - ONE /players model: test_one_function_scales_odds_by_players.
The page's own engine (cut from bible.html) runs in node; every expectation is recomputed from the vendored raw
probabilities, never typed. A stored base is the page's; this law certifies the factor applied to it, and checks
separately that the base is this pull's /players 1 figure. RED_PROOF below.
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
DATA = os.path.join(HERE, "data", "silospen_players_rotw30.json")
NODE = shutil.which("node")
TIERS = ("norm", "nm", "hell", "normTz", "nmTz", "hellTz")      # every column the page stores, terror zones included
EPS = 0.00025                     # the measured reach of one factor per cell over the whole pull (0.0152%), rounded up
ROUNDING = 0.5e-11                # silospen prints 11 decimals: a 1:150,000,000 item carries only 3 significant digits
# a farm whose stored /players 1 odds are NOT this pull's, with the reason - refused as stale once they agree
BASE_NOT_THIS_PULL = {}           # REG-2954 closed it: the Pit is Pit Level 1's Devilkin, and every column now agrees
SEC_START = '<span class="sec-h-t">What the P# slider actually does</span>'


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


def _bosses(src):
    line = next(ln for ln in src.split("\n") if ln.startswith("const BOSSES = "))
    body = line[len("const BOSSES = "):]
    return {b["id"]: b for b in json.loads(body[:body.rindex("];") + 1])}


def _code(src):
    """bible.html with its comments removed: bounded block comments (an unbounded /* ... */ match runs through a
    string's '/*' to the next '*/' anywhere in the file) and line comments."""
    src = re.sub(r"/\*.{0,4000}?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(^|[^:\\'\"])//[^\n]*", r"\1", src)


def _round(x):
    return int(math.floor(x + 0.5))


def _near(got, want, ps=()):
    """within one count, or EPS of N plus what silospen's own 11-decimal rounding of the probabilities `ps` can move N."""
    slack = want * (EPS + sum(ROUNDING / p for p in ps))
    return got is not None and abs(got - want) <= max(1, int(math.ceil(slack)))


def _stored(boss, tier):
    """name -> the page's stored 1:N; silospen's bare name also finds the page's "Name (alias)" row."""
    out = {}
    for r in boss["dropTable"]:
        v = r.get(tier)
        out.setdefault(r["n"], v)
        out.setdefault(re.sub(r"\s*\([^)]*\)$", "", r["n"]), v)
    return out


def _node(prog):
    r = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise AssertionError("node failed: " + (r.stderr or r.stdout)[-2500:])
    return json.loads(r.stdout.strip().splitlines()[-1])


SCENARIO = r"""
var out = { eff: [], mult: {} };
CASES.forEach(function(c){ mf = c[4]; players = c[3]; out.eff.push(effChance(c[2], c[0], c[1])); });
SUBJECTS.forEach(function(s){
  out.mult[s] = {};
  ['norm', 'nm', 'hell', 'normTz', 'nmTz', 'hellTz'].forEach(function(t){
    out.mult[s][t] = [1, 2, 3, 4, 5, 6, 7, 8].map(function(p){ return playerMult(s, t, p); });
  });
});
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, "node is required to drive the page's own drop math")
class PlayersMovesOddsBySilospensOwnFactor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.src = _read()
        cls.data = _data()
        cls.bosses = _bosses(cls.src)
        cls.cases, cls.want = [], []      # [subject, tier, stored base, players, MF] -> (label, silospen's 1:N)
        for subj, ent in sorted(cls.data["subjects"].items()):
            for t in TIERS:
                stored = _stored(cls.bosses[subj], t)
                for name, it in sorted(ent[t]["items"].items()):
                    base, p1 = stored.get(name), it["p"]["1"]
                    for lvl, p in sorted(it["p"].items(), key=lambda kv: int(kv[0])):
                        cls.cases.append([subj, t, base, int(lvl), 300])
                        # the factor silospen gives, applied to the page's own base
                        cls.want.append((name, _round(base * p1 / p) if base else None, (p1, p)))
        mfd = cls.data.get("mf") or {}
        stored = _stored(cls.bosses[mfd["subject"]], mfd["difficulty"]) if mfd else {}
        for mf, at in sorted((mfd.get("at") or {}).items()):
            for lvl, items in sorted(at.items()):
                for name, p in sorted(items.items()):
                    cls.cases.append([mfd["subject"], mfd["difficulty"], stored.get(name), int(lvl), int(mf)])
                    cls.want.append(("%s at MF %s" % (name, mf), _round(1.0 / p), (p,)))
        engine = _cut(cls.src, "const effMF = (gMF, factor) =>", "// GRAIL-FARM BRIDGE")
        prelude = ("var window = {}; var document = { getElementById: function(){ return null; } };\n"
                   "var mf = 300, players = 1;\nvar CASES = %s;\nvar SUBJECTS = %s;\n"
                   % (json.dumps(cls.cases), json.dumps(sorted(cls.data["subjects"]))))
        cls.o = _node(prelude + engine + "\n" + SCENARIO)

    def test_the_pull_is_the_source_the_page_stores(self):
        d = self.data
        for part in ("version=D2R_ROW_3_0", "party=1", "desecrated={TZ}", "desecratedLevel={LEVEL}"):
            self.assertIn(part, d["query"], "the pull is not the one the stored 1:N came from: %s" % part)
        self.assertEqual(d["magicFind"], 300, "the stored bases are silospen's at MF 300")
        self.assertEqual(sorted(d["tz"]["desecratedLevel"]), ["hellTz", "nmTz", "normTz"],
                         "premise: every terror-zone column names the level it was pulled at")
        f = json.loads(re.search(r"const PLAYER_F = (\{.*?\});\n", self.src).group(1))
        self.assertEqual(sorted(f), sorted(d["subjects"]), "the page scales a farm the pull does not cover, or the reverse")
        checked, off = 0, {}
        for subj, ent in d["subjects"].items():
            for t in TIERS:
                stored = _stored(self.bosses[subj], t)
                self.assertGreaterEqual(len(ent[t]["items"]), 4, "%s %s: too few items vendored" % (subj, t))
                for name, it in ent[t]["items"].items():
                    base = stored.get(name)
                    self.assertTrue(base and base > 1, "%s %s %s: the page stores no 1:N for a vendored item" % (subj, t, name))
                    if not _near(base, _round(1.0 / it["p"]["1"]), (it["p"]["1"],)):
                        off.setdefault(subj, []).append("%s %s: 1:%s, pull 1:%d" % (t, name, base, _round(1.0 / it["p"]["1"])))
                    checked += 1
        self.assertGreaterEqual(checked, 4 * 11 * 6, "premise: items enough to read every farm and column")
        self.assertEqual(sorted(off), sorted(BASE_NOT_THIS_PULL),
                         "stored /players 1 odds disagree with the pull outside the declared farms, or a declared farm "
                         "now agrees (drop its declaration): %r" % {k: v[:3] for k, v in off.items()})

    def test_the_page_steps_exactly_where_silospen_steps(self):
        series = 0
        for subj, ent in self.data["subjects"].items():
            for t in TIERS:
                m = self.o["mult"][subj][t]
                self.assertEqual(m[0], 1, "%s %s: /players 1 is not the x1.00 baseline" % (subj, t))
                for name, it in ent[t]["items"].items():
                    p = [it["p"].get(str(k)) for k in range(1, 9)]
                    if None in p:
                        continue
                    series += 1
                    game = [abs(p[i + 1] - p[i]) > p[i] * 1e-6 for i in range(7)]
                    page = [m[i + 1] != m[i] for i in range(7)]
                    self.assertEqual(page, game, "%s %s (%s): the page steps at /players %s, silospen at %s"
                                     % (subj, t, name, [i + 2 for i, x in enumerate(page) if x],
                                        [i + 2 for i, x in enumerate(game) if x]))
        self.assertGreaterEqual(series, 2 * 11 * 6, "premise: full /players 1-8 series for every farm and column")
        # the general shape the explainer states, read from the data rather than typed
        pairs = sum(1 for s in self.o["mult"].values() for m in s.values()
                    if m[0] == m[1] and m[2] == m[3] and m[4] == m[5] and m[6] == m[7])
        self.assertGreaterEqual(pairs, 11 * 6 - 3, "premise: the 1=2, 3=4, 5=6, 7=8 pairing holds on all but three "
                                                   "columns (Hell Duriel; Andariel's Nightmare and Hell terror zones)")

    def test_every_vendored_item_prints_silospens_odds(self):
        bad = []
        for (name, want, ps), case, got in zip(self.want, self.cases, self.o["eff"]):
            if want is None or not _near(got, want, ps):
                bad.append("%s %s %s /p%d MF %d: page 1:%s, silospen 1:%s" % (case[0], case[1], name, case[3], case[4], got, want))
        self.assertGreaterEqual(len(self.cases), 900, "premise: the vendored pull is read")
        self.assertEqual(bad, [], "%d of %d printed odds are not silospen's: %s" % (len(bad), len(self.cases), bad[:8]))

    def test_only_a_table_that_does_not_move_is_called_proof_against_players(self):
        still = set()
        for subj, ent in self.data["subjects"].items():
            moves = any(abs(it["p"][k] - it["p"]["1"]) > it["p"]["1"] * 1e-6
                        for t in TIERS for it in ent[t]["items"].values() for k in it["p"])
            self.assertEqual(any(x != 1 for t in TIERS for x in self.o["mult"][subj][t]), moves,
                             "%s: silospen %s it with /players and the page %s" % (subj, "moves" if moves else "does not move",
                                                                                 "does not" if moves else "does"))
            if not moves:
                still.add(subj)
        self.assertEqual(still, {"pindle"}, "premise: the pull's one unmoved farm is Pindleskin")
        sec = _cut(self.src, SEC_START, "\n  </div>\n")
        rows = re.findall(r"<tr><td class=\"item-name\">[^<]*</td><td>([^<]+)</td>(.*?)</tr>", sec)
        proof = [b for b, rest in rows if "P#-PROOF" in rest]
        self.assertEqual([b.strip() for b in proof], ["Pindleskin"], "the P# table tags another farm P#-PROOF: %r" % proof)
        self.assertNotIn("guaranteed dropper", sec.lower(), "the P# section still calls a moving farm a guaranteed dropper")
        tip = re.search(r'data-tip="/players N[^"]*"', self.src).group(0)
        myth = _cut(self.src, 'label: "PLAYERS=8 MYTH"', "\n  },\n")
        for said in (tip, myth):
            self.assertRegex(said, r"nothing</?(?:strong>)? for Pindleskin|nothing for Pindleskin")
            self.assertNotIn("guaranteed droppers (Countess", said, "a tip still says /players moves nothing for Countess")

    def test_one_function_scales_odds_by_players(self):
        """His ruling (#190 Q7, 2026-10-29): silospen and its logic are the truth, and /players is ONE joined model -
        no second formula anywhere. Swept 2026-10-29: effChance, _adjC (the MF-blind path), the boss-nav and boss-card
        tier multipliers and the hero P#-PROOF tag all ask playerMult, and the console computes no /players odds of its
        own (it reads the page's adjusted d2r_grailFarm). This holds the join: the factor table is read only inside
        playerMult, both odds paths call it, and the retired model's shapes are gone from the code."""
        code = _code(self.src)
        self.assertEqual(code.count("PLAYER_F"), 2, "the factor table is read outside playerMult - a second /players path")
        pm = _cut(code, "function playerMult(bossId, diffKey, players){", "\n    }\n")
        self.assertIn("PLAYER_F[", pm, "premise: playerMult reads the factor table")
        for start, name in (("function effChance(base, bossId, diffKey){", "effChance"),
                            ("function _adjC(s, name){", "the MF-blind path (_adjC)")):
            body = _cut(code, start, "\n    }\n" if name == "effChance" else "\n  }\n")
            self.assertIn("playerMult(", body, "%s scales odds by /players without playerMult" % name)
        self.assertNotIn("PLAYER_Q", code, "the retired one-NoDrop table is back")
        for pat in (r"Math\.(?:floor|ceil)\(\s*\(*\s*players", r"\bplayers\s*>>\s*1", r"Math\.pow\(\s*q\s*,"):
            self.assertIsNone(re.search(pat, code), "a second /players formula is in the code: %s" % pat)

    def test_the_explainer_states_the_measured_steps(self):
        sec = _cut(self.src, SEC_START, "\n  </div>\n")
        self.assertIn("/p1=/p2, /p3=/p4, /p5=/p6, /p7=/p8", sec, "the explainer does not state the pairing the game uses")
        self.assertNotIn("floor(N / 2)", sec, "the explainer still states the retired k = 1 + floor(N / 2) model")
        self.assertIn("silospen", sec, "the explainer does not name the source of its factors")


RED_PROOF = [
    {"why": "#190 Q7 - the MF-blind path scales by its own /players formula instead of playerMult",
     "file": "bible.html",
     "find": "        var m = playerMult(s.bossId, s.diffKey, (typeof players!=='undefined'?players:1));\n",
     "replace": "        var m = 1 + 0.1 * Math.floor(((typeof players!=='undefined'?players:1) - 1) / 2);\n",
     "matches": 1, "needs": "node"},
    {"why": "#190 Q7 - a tier multiplier reads the factor table itself, a second /players path",
     "file": "bible.html",
     "find": "    const ms = g.members.filter(id => __bossOf[id]).map(id => playerMult(id, 'hell', players));\n",
     "replace": "    const ms = g.members.filter(id => __bossOf[id]).map(id => (PLAYER_F[id] || {}).hell ? PLAYER_F[id].hell[players - 1] : 1);\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2953 - /players steps on the retired k = 1 + floor(players / 2) pairing (2=3, 4=5, 6=7)",
     "file": "bible.html",
     "find": "      var n = Math.max(1, Math.min(8, Math.round(players||1)));\n",
     "replace": "      var n = Math.max(1, Math.min(8, 2 * Math.floor((players||1) / 2)));\n",
     "matches": 1, "needs": "node"},
    {"why": "REG-2953 - Countess is held at x1.00 again (a 'guaranteed dropper' the data moves)",
     "file": "bible.html",
     "find": "\"countess\":{\"norm\":[1,1,1.28844,1.28844,1.36732,1.36732,1.39581,1.39581]",
     "replace": "\"countess\":{\"norm\":[1,1,1,1,1,1,1,1]",
     "matches": 1, "needs": "node"},
    {"why": "REG-2953 - Andariel's size is the one-NoDrop model's again (x1.39 at /p8 where silospen gives x1.78)",
     "file": "bible.html",
     "find": "\"andariel\":{\"norm\":[1,1,1.46417,1.46417,1.70814,1.70814,1.78238,1.78238]",
     "replace": "\"andariel\":{\"norm\":[1,1,1.28358,1.28358,1.36398,1.36398,1.38682,1.38682]",
     "matches": 1, "needs": "node"},
    {"why": "REG-2953 - Hell Duriel loses the 1.4% the game gives at /players 2",
     "file": "bible.html",
     "find": "\"hell\":[1,1.01449,1.27272,",
     "replace": "\"hell\":[1,1,1.27272,",
     "matches": 1, "needs": "node"},
    {"why": "REG-2953 - the P# table tags Countess and Duriel P#-PROOF again",
     "file": "bible.html",
     "find": "<td>Countess · Duriel</td><td>×1.27–1.28</td><td>×1.37–1.39</td>",
     "replace": "<td>Countess · Duriel</td><td>×1.27–1.28</td><td><strong>×1.00 · P#-PROOF</strong></td>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2953 - the explainer states the retired pairing",
     "file": "bible.html",
     "find": "the game pairs <strong>/p1=/p2, /p3=/p4, /p5=/p6, /p7=/p8</strong>",
     "replace": "the game pairs <strong>/p2=/p3, /p4=/p5, /p6=/p7</strong>",
     "matches": 1, "needs": "node"},
    {"why": "REG-2955 - Andariel's Hell terror zone takes its difficulty's /players factor again",
     "file": "bible.html",
     "find": "\"hellTz\":[1,1.00787,1.45454,1.45454,1.66232,1.66232,1.75341,1.75341]",
     "replace": "\"hellTz\":[1,1,1.48275,1.48275,1.65383,1.65383,1.79165,1.79165]",
     "matches": 1, "needs": "node"},
    {"why": "REG-2955 - playerMult ignores a column's terror-zone twin",
     "file": "bible.html",
     "find": "      if (/Tz$/.test(diffKey)) tier += 'Tz';   // REG-2955 \u2014 a terror zone's own measured factor\n",
     "replace": "",
     "matches": 1, "needs": "node"},
    {"why": "REG-2954 - the Pit's Nightmare column is Pit Level 2's again (Venom Ward 1:104,359 where Pit Level 1 gives 1:104,635)",
     "file": "bible.html",
     "find": "\"n\":\"Venom Ward\",\"tc\":15,\"qlvl\":20,\"tier\":\"common\",\"norm\":null,\"normTz\":109957,\"nm\":104635,",
     "replace": "\"n\":\"Venom Ward\",\"tc\":15,\"qlvl\":20,\"tier\":\"common\",\"norm\":null,\"normTz\":109957,\"nm\":104359,",
     "matches": 1, "needs": "node"},
]

if __name__ == "__main__":
    unittest.main(verbosity=2)
